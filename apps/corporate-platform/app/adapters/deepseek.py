"""DeepSeek 适配器 — OpenAI 兼容接口"""

from app.adapters.base import ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.config import settings


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        model_info=ModelInfo(
            model_id="deepseek-v4-pro",
            display_name="DeepSeek V4 Pro",
            provider="DeepSeek",
            provider_key="deepseek",
            description="DeepSeek 最新模型（纯文本，不支持图片）",
            capabilities=["text"],
        ),
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
