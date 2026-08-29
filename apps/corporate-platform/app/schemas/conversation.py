"""对话会话相关 Pydantic Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    images: list | None = None
    reasoning_content: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """创建新对话"""
    title: str = "新对话"
    model: str = "deepseek-v4-pro"
    conv_type: str = "chat"  # chat / discuss


class ConversationUpdate(BaseModel):
    """更新对话标题"""
    title: str


class ConversationSummary(BaseModel):
    """对话列表摘要"""
    id: int
    title: str
    model: str
    conv_type: str = "chat"
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """对话详情（含消息列表）"""
    id: int
    title: str
    model: str
    conv_type: str = "chat"
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True
