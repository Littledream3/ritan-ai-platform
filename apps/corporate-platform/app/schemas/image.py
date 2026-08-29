"""图片生成 — 请求/响应 Schema"""

from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    """文生图请求"""

    model: str
    prompt: str = Field(..., min_length=1, max_length=5000)
    size: str | None = None
    n: int = Field(default=1, ge=1, le=4)
    quality: str | None = None
    response_format: str = Field(default="url")


class ImageModelInfo(BaseModel):
    """图片模型信息 — 用于前端模型选择器"""

    model_id: str
    display_name: str
    provider: str
    description: str
    available: bool
    sizes: list[str]
    default_size: str
    qualities: list[str] | None = None
    formats: list[str] | None = None
