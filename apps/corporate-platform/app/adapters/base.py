"""模型适配器抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class ModelInfo:
    """模型元信息"""
    model_id: str
    display_name: str
    provider: str
    provider_key: str = ""      # 机器可读: deepseek/kimi/qwen/glm/doubao
    description: str = ""
    available: bool = True
    capabilities: list[str] = field(default_factory=lambda: ["chat"])


class BaseAdapter(ABC):
    """所有模型适配器的抽象基类"""

    model_info: ModelInfo

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **params,
    ) -> dict:
        """
        非流式对话

        Args:
            messages: [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            **params: 模型特定参数

        Returns:
            OpenAI-compatible 响应格式:
            {
                "id": "...",
                "model": "...",
                "choices": [{"message": {"role": "assistant", "content": "..."}}],
                "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
            }
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **params,
    ) -> AsyncGenerator[dict, None]:
        """
        流式对话 — 异步生成器，逐块产出 delta

        Yields:
            {"delta": {"content": "片段"}, "finish_reason": None | "stop"}
        """
        ...
