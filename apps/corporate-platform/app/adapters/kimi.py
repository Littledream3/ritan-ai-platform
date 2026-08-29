"""Kimi 适配器 — Moonshot API（OpenAI 兼容）"""

from app.adapters.base import ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.config import settings


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        model_info=ModelInfo(
            model_id="kimi-k2.7-code",
            display_name="Kimi K2.7 Code",
            provider="月之暗面 (Moonshot)",
            provider_key="kimi",
            description="Kimi 最新模型（代码增强，支持图片识别）",
            capabilities=["text", "vision"],
        ),
        api_key=settings.kimi_api_key,
        base_url=settings.kimi_base_url,
    )
