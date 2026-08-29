"""GLM 适配器 — 智谱 API（OpenAI 兼容）"""

from app.adapters.base import ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.config import settings


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        model_info=ModelInfo(
            model_id="glm-4.7",
            display_name="GLM 4.7",
            provider="智谱 (Zhipu)",
            provider_key="glm",
            description="智谱 GLM 免费版（纯文本，不支持图片）",
            capabilities=["text"],
        ),
        api_key=settings.glm_api_key,
        base_url=settings.glm_base_url,
    )
