"""对话管理 API — CRUD"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/api/v1/conversations", tags=["对话管理"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    conv_type: str = Query(default="chat", description="对话类型: chat / discuss"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有对话摘要（可按类型筛选）"""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user.id,
            Conversation.conv_type == conv_type,
        )
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    summaries = []
    for conv in conversations:
        # 取最后一条消息作为预览
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()
        summaries.append(ConversationSummary(
            id=conv.id,
            title=conv.title,
            model=conv.model,
            conv_type=conv.conv_type,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message=last_msg.content[:80] if last_msg and last_msg.content else None,
        ))

    return summaries


@router.post("", response_model=ConversationDetail)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    conv = Conversation(
        user_id=user.id,
        title=body.title,
        model=body.model,
        conv_type=body.conv_type,
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        conv_type=conv.conv_type,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情（含全部消息）"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 加载消息
    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    messages = msgs_result.scalars().all()

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        conv_type=conv.conv_type,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.put("/{conv_id}")
async def update_conversation(
    conv_id: int,
    body: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名对话"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    conv.title = body.title
    await db.flush()
    return {"ok": True}


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话（级联删除消息）"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    await db.delete(conv)
    await db.flush()
    return {"ok": True}
