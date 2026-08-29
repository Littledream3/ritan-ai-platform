"""AI 多模型辩论 — 请求/响应 Schema"""

from pydantic import BaseModel, Field


class DiscussRequest(BaseModel):
    """多模型讨论请求"""

    question: str = Field(..., min_length=1, max_length=10000)
    models: list[str] = Field(..., min_items=2, max_items=5)  # 至少 2 个，最多 5 个
    rounds: int = Field(default=3, ge=2, le=3)                # 2-3 轮
    images: list[str] | None = Field(default=None, max_items=500)  # base64 data URLs
    videos: list[str] | None = Field(default=None, max_items=20)  # 视频 URLs

    # 新增：对话管理 + 深度思考 + 记忆
    conversation_id: int | None = Field(default=None)         # 关联已有对话
    title: str | None = Field(default=None, max_length=255)   # 新对话标题
    thinking: bool = Field(default=False)                      # 深度思考模式
    enable_search: bool = Field(default=False)                 # 联网搜索
    memory: bool = Field(default=False)                        # 记忆模式（注入历史上下文）
