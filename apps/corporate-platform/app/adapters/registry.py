"""模型注册中心 — 管理所有模型适配器的注册与查询"""

from loguru import logger

from app.adapters.base import BaseAdapter, ModelInfo
from app.adapters.openai_compatible import OpenAICompatibleAdapter

# 导入各适配器的工厂函数
from app.adapters import deepseek, kimi, qwen, glm, doubao


class ModelRegistry:
    """模型注册中心

    用法:
        registry = ModelRegistry()
        registry.init()                         # 注册所有模型
        adapter = registry.get("deepseek-v4-pro")
        models = registry.list_models()
    """

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    @property
    def is_initialized(self) -> bool:
        return len(self._adapters) > 0

    def init(self) -> None:
        """初始化 — 注册全部 5 个模型适配器"""
        self._register_all()

    def register(self, adapter: BaseAdapter) -> None:
        """注册单个适配器"""
        model_id = adapter.model_info.model_id
        has_key = self._has_api_key(adapter)
        # 尊重适配器自身的 available 设置（如欠费主动标记为 False）
        adapter.model_info.available = has_key and adapter.model_info.available
        self._adapters[model_id] = adapter
        if not has_key:
            status = "⚠️ 未配置 API Key"
        elif not adapter.model_info.available:
            status = "❌ 不可用"
        else:
            status = "✅"
        logger.info(f"  {adapter.model_info.display_name} ({model_id}) → {status}")

    def get(self, model_id: str) -> BaseAdapter:
        """根据 model_id 获取适配器

        Raises:
            ValueError: 模型不存在
        """
        if not self._adapters:
            self.init()

        adapter = self._adapters.get(model_id)
        if adapter is None:
            available = ", ".join(self._adapters.keys())
            raise ValueError(f"未知模型 '{model_id}'，可用: {available}")
        return adapter

    def list_models(self) -> list[dict]:
        """列出所有已注册模型的信息"""
        if not self._adapters:
            self.init()

        return [
            {
                "model_id": a.model_info.model_id,
                "display_name": a.model_info.display_name,
                "provider": a.model_info.provider,
                "description": a.model_info.description,
                "available": a.model_info.available,
                "capabilities": a.model_info.capabilities,
            }
            for a in self._adapters.values()
        ]

    # ---- 私有 ----

    def _register_all(self) -> None:
        """注册全部 5 个模型"""
        logger.info("📋 注册模型适配器...")

        factories = [
            ("deepseek", deepseek.create_adapter),
            ("kimi", kimi.create_adapter),
            ("qwen", qwen.create_adapter),
            ("glm", glm.create_adapter),
            ("doubao", doubao.create_adapter),
        ]

        for name, factory in factories:
            try:
                adapter = factory()
                self.register(adapter)
            except Exception as e:
                logger.error(f"  ❌ {name} 注册失败: {e}")

    def _has_api_key(self, adapter: BaseAdapter) -> bool:
        """检查适配器是否配置了有效的 API Key"""
        if isinstance(adapter, OpenAICompatibleAdapter):
            key = adapter._api_key
            return bool(key) and key not in ("", "your_api_key_here")
        return False


# 全局单例
registry = ModelRegistry()
