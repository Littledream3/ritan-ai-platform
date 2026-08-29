"""视频生成 — 请求/响应 Schema"""

from pydantic import BaseModel, Field


class VideoGenerationRequest(BaseModel):
    """文生视频请求"""

    model: str
    prompt: str = Field(..., min_length=1, max_length=3000)
    resolution: str | None = None
    ratio: str | None = None
    duration: int = Field(default=5, ge=2, le=15)
    quality: str | None = None
    fps: int | None = None
    with_audio: bool = True
    watermark: bool = False


class VideoModelInfo(BaseModel):
    """视频模型信息 — 用于前端模型选择器"""

    model_id: str
    display_name: str
    provider: str
    description: str
    available: bool
    resolutions: list[str]
    default_resolution: str
    ratios: list[str]
    max_duration: int
    durations: list[int]
    qualities: list[str] | None = None
    fps_options: list[int] | None = None
