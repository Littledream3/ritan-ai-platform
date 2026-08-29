"""对话相关 Pydantic Schema"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条消息 — content 支持纯文本或 OpenAI 多模态格式"""
    role: str
    content: str | list  # str: 纯文本; list: [{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"data:..."}}]
    name: str | None = None


class ChatRequest(BaseModel):
    """对话请求"""
    model: str
    messages: list[ChatMessage]
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int = Field(default=8192, ge=1, le=128000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    conversation_id: int | None = None  # 可选，关联到已有对话
    enable_search: bool = False  # 是否启用联网搜索
    thinking: bool = False  # 是否启用深度思考/推理模式
