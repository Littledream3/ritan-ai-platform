"""Qwen 适配器 — 阿里云百炼 DashScope（OpenAI 兼容模式）

⚠️ 当前状态：账户欠费停服，所有模型不可用。
   充值后恢复：https://help.aliyun.com/zh/model-studio/error-code#overdue-payment
"""

from app.adapters.base import ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.config import settings


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        model_info=ModelInfo(
            model_id="qwen3.7-max",
            display_name="Qwen 3.7 Max",
            provider="阿里云百炼 (DashScope)",
            provider_key="qwen",
            description="❌ 欠费停服 — 充值后可恢复使用",
            available=False,
            capabilities=["text", "vision"],
        ),
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
    )
