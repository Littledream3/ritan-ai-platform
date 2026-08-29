"""豆包适配器 — 火山引擎 Ark（OpenAI 兼容）

当前使用 Lite 免费版（Pro 版达限额，充值后可切回）。
"""

from app.adapters.base import ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.config import settings


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        model_info=ModelInfo(
            model_id="doubao-seed-2-0-lite-260215",
            display_name="豆包 Seed 2.0 Lite（免费版）",
            provider="字节跳动 (火山引擎)",
            provider_key="doubao",
            description="豆包免费 Lite 版（Pro 需充值解锁限额）",
            capabilities=["text", "vision"],
        ),
        api_key=settings.doubao_api_key,
        base_url=settings.doubao_base_url,
    )
