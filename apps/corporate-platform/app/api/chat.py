"""对话 API — 非流式 + SSE 流式"""

import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import registry
from app.core.database import async_session, get_db
from app.middleware.auth import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.models.usage_log import UsageLog
from app.schemas.chat import ChatRequest
from app.services.stats_service import record_chat

router = APIRouter(prefix="/api/v1", tags=["对话"])


# ---- 非流式对话 ----

@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """非流式对话 — 等待完整回复后一次性返回"""
    try:
        adapter = registry.get(body.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not adapter.model_info.available:
        raise HTTPException(
            status_code=503,
            detail=f"模型 '{body.model}' 不可用（API Key 未配置）",
        )

    # 校验消息列表
    if not body.messages:
        raise HTTPException(status_code=400, detail="消息列表不能为空")

    # 解析 messages，提取最后一条用户消息的文本和图片
    user_msg = body.messages[-1]
    user_text = user_msg.content if isinstance(user_msg.content, str) else ""
    user_images = user_msg.content if isinstance(user_msg.content, list) else None

    messages = [m.model_dump(exclude_none=True) for m in body.messages]

    # 构建可选参数
    extra_params = {}
    if body.temperature is not None:
        extra_params["temperature"] = body.temperature
    if body.top_p is not None:
        extra_params["top_p"] = body.top_p
    if body.enable_search:
        extra_params["enable_search"] = True
    if body.thinking:
        extra_params["thinking"] = True

    # 确保 conversation 存在
    conv = await _get_or_create_conv(db, user, body)

    # 存储用户消息
    _save_message(db, conv.id, "user", user_text, user_images)

    start = time.time()
    try:
        result = await adapter.chat(
            messages=messages,
            max_tokens=body.max_tokens,
            **extra_params,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"模型 '{body.model}' 调用失败: {str(e)}",
        )

    latency_ms = int((time.time() - start) * 1000)

    # 存储助手回复（含推理过程）
    choice_msg = result.get("choices", [{}])[0].get("message", {})
    assistant_text = choice_msg.get("content", "")
    reasoning_content = choice_msg.get("reasoning_content") or ""
    _save_message(db, conv.id, "assistant", assistant_text, reasoning=reasoning_content or None)

    # 更新对话标题（取第一条用户消息前 30 字）
    if conv.title == "新对话" and user_text:
        conv.title = user_text[:30]
        # 统计该对话的消息数，如果是第一条则用用户消息做标题
        msg_count_result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        # 只有第一条消息时更新标题
        all_msgs = msg_count_result.scalars().all()
        if len(all_msgs) <= 2:  # user + assistant = 2
            conv.title = user_text[:30] + ("..." if len(user_text) > 30 else "")

    # 记录用量
    usage = result.get("usage", {})
    log = UsageLog(
        user_id=user.id,
        model=body.model,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        latency_ms=latency_ms,
    )
    db.add(log)

    await record_chat(
        user_id=user.id,
        model=body.model,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
    )

    return result


# ---- SSE 流式对话 ----

@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式对话 — 逐 token 推送回复内容"""
    try:
        adapter = registry.get(body.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not adapter.model_info.available:
        raise HTTPException(
            status_code=503,
            detail=f"模型 '{body.model}' 不可用（API Key 未配置）",
        )

    # 校验消息列表
    if not body.messages:
        raise HTTPException(status_code=400, detail="消息列表不能为空")

    # 解析用户消息
    user_msg = body.messages[-1]
    user_text = user_msg.content if isinstance(user_msg.content, str) else ""
    user_images = user_msg.content if isinstance(user_msg.content, list) else None

    messages = [m.model_dump(exclude_none=True) for m in body.messages]
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

    # 构建可选参数
    extra_params = {}
    if body.temperature is not None:
        extra_params["temperature"] = body.temperature
    if body.top_p is not None:
        extra_params["top_p"] = body.top_p
    if body.enable_search:
        extra_params["enable_search"] = True
    if body.thinking:
        extra_params["thinking"] = True

    # 确保 conversation 存在
    conv = await _get_or_create_conv(db, user, body)

    # 存储用户消息并 flush
    _save_message(db, conv.id, "user", user_text, user_images)

    # 更新对话标题
    if conv.title == "新对话" and user_text:
        msg_count_result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        all_msgs = msg_count_result.scalars().all()
        if len(all_msgs) <= 1:
            conv.title = user_text[:30] + ("..." if len(user_text) > 30 else "")

    # 确保用户消息已持久化
    await db.flush()

    # 缓存 generator 需要的数据（db session 在 generator 内不可用）
    _conv_id = conv.id
    _user_id = user.id
    _model = body.model

    async def sse_generator():
        full_content = ""
        full_reasoning = ""
        completion_tokens = 0
        try:
            async for chunk in adapter.chat_stream(
                messages=messages,
                max_tokens=body.max_tokens,
                **extra_params,
            ):
                delta = chunk.get("delta", {})
                content = delta.get("content")
                if content:
                    completion_tokens += len(content)
                    full_content += content
                # 累积推理内容
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    full_reasoning += reasoning
                event = {
                    "id": chunk_id,
                    "model": _model,
                    "choices": [{
                        "index": 0,
                        "delta": delta,
                        "finish_reason": chunk.get("finish_reason"),
                    }],
                }
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 用新 session 保存助手消息（含推理过程）
            if full_content:
                async with async_session() as s2:
                    s2.add(Message(
                        conversation_id=_conv_id,
                        role="assistant",
                        content=full_content,
                        reasoning_content=full_reasoning or None,
                    ))
                    await s2.commit()

            await record_chat(
                user_id=_user_id,
                model=_model,
                prompt_tokens=0,
                completion_tokens=completion_tokens,
            )
        except Exception as e:
            error_event = {
                "error": {"message": str(e), "type": "api_error"}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---- 辅助函数 ----

async def _get_or_create_conv(db: AsyncSession, user: User, body: ChatRequest) -> Conversation:
    """获取或创建对话"""
    if body.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    conv = Conversation(user_id=user.id, title="新对话", model=body.model)
    db.add(conv)
    await db.flush()
    return conv


def _save_message(
    db: AsyncSession,
    conv_id: int,
    role: str,
    content: str,
    images: list | None = None,
    reasoning: str | None = None,
):
    """保存消息到数据库（异步），不阻塞主流程"""
    msg = Message(
        conversation_id=conv_id,
        role=role,
        content=content if content else "",
        images=images,
        reasoning_content=reasoning,
    )
    db.add(msg)
