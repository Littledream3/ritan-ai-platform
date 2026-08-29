"""AI 多模型辩论 API"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.discuss import DiscussRequest
from app.services.discuss_service import run_discuss

router = APIRouter(prefix="/api/v1", tags=["AI 辩论"])


async def _get_or_create_discuss_conv(
    db: AsyncSession,
    user_id: int,
    conv_id: int | None,
    title: str | None,
    question: str,
) -> Conversation:
    """获取或创建讨论对话"""
    if conv_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv
        # 如果对话不存在，fall through 创建新的

    conv = Conversation(
        user_id=user_id,
        title=title or (question[:50] + ("..." if len(question) > 50 else "")),
        model=",".join([]),  # 讨论使用多模型，稍后更新
        conv_type="discuss",
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def _build_memory_context(db: AsyncSession, conv_id: int) -> str | None:
    """从对话历史中构建记忆上下文"""
    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    messages = msgs_result.scalars().all()
    if not messages:
        return None

    # 提取用户问题和较短的模型回复作为记忆摘要
    # 长回复通常是讨论中间过程，跳过；短回复（≤200字）通常是结论/摘要
    parts = []
    for m in messages:
        if m.role == "user" and m.content:
            parts.append(f"[用户提问] {m.content[:200]}")
        elif m.role == "assistant" and m.content:
            if len(m.content) <= 200:
                parts.append(f"[模型回复] {m.content}")

    if not parts:
        return None

    return "\n".join(parts[-10:])  # 最近 10 条（含问答对）


@router.post("/discuss")
async def discuss(
    body: DiscussRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多模型辩论 — SSE 流式返回讨论过程

    事件类型:
      start       — 讨论开始，包含 question / models / model_names
      round_start — 新一轮开始，包含 round / label
      round_result— 某个模型完成本轮回答，包含 round / model / content / reasoning_content
      final       — 最终总结
      error       — 某个模型出错
      done        — 讨论结束
    """
    # 校验模型数量
    if len(body.models) < 2:
        raise HTTPException(status_code=400, detail="至少选择 2 个模型参与讨论")

    # 获取或创建对话
    conv = await _get_or_create_discuss_conv(
        db, user.id, body.conversation_id, body.title, body.question,
    )

    # 更新对话模型列表
    conv.model = ",".join(body.models)
    await db.flush()

    # 保存用户问题消息
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=body.question,
        images=body.images,
    )
    db.add(user_msg)
    await db.flush()

    # 构建记忆上下文
    memory_context = None
    if body.memory and body.conversation_id:
        memory_context = await _build_memory_context(db, body.conversation_id)

    logger.info(
        f"🗣️ 用户 {user.username} 发起辩论 conv_id={conv.id} models={body.models} "
        f"rounds={body.rounds} thinking={body.thinking} memory={body.memory} "
        f"question={body.question[:50]}..."
    )

    async def sse_wrapper():
        # 收集各轮结果用于持久化
        round_results: list[dict] = []
        final_content = ""
        final_reasoning = None
        final_model_name = ""

        try:
            async for event in run_discuss(
                question=body.question,
                models=body.models,
                rounds=body.rounds,
                images=body.images,
                videos=body.videos,
                thinking=body.thinking,
                enable_search=body.enable_search,
                memory_context=memory_context,
            ):
                # 解析事件收集数据用于持久化
                try:
                    data_str = event.strip()
                    if data_str.startswith("data:"):
                        data_str = data_str[5:].strip()
                    event_data = json.loads(data_str)

                    if event_data.get("type") == "round_result":
                        round_results.append(event_data)
                    elif event_data.get("type") == "final":
                        final_content = event_data.get("content", "")
                        final_reasoning = event_data.get("reasoning_content")
                        final_model_name = event_data.get("model_name", "")
                except (json.JSONDecodeError, KeyError):
                    pass

                yield event
        except Exception as e:
            logger.exception(f"辩论异常: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 持久化讨论结果
            try:
                # 保存各模型的轮次回复
                for rr in round_results:
                    content = rr.get("content", "")
                    reasoning = rr.get("reasoning_content")
                    model_name = rr.get("model_name", "")
                    round_num = rr.get("round", 0)

                    msg = Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content=f"[第{round_num}轮] {model_name}:\n{content}",
                        reasoning_content=reasoning,
                    )
                    db.add(msg)

                # 保存最终结论
                if final_content:
                    final_msg = Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content=f"[最终结论] {final_model_name}:\n{final_content}",
                        reasoning_content=final_reasoning,
                    )
                    db.add(final_msg)

                await db.flush()
            except Exception as e:
                logger.error(f"持久化讨论结果失败: {e}")

    return StreamingResponse(
        sse_wrapper(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
