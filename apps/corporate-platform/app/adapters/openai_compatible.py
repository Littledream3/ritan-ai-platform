"""OpenAI 兼容接口通用适配器

适用于所有提供 OpenAI Chat Completions 兼容端点的模型：
DeepSeek / Kimi / Qwen / GLM / 豆包
"""

import json
from typing import AsyncGenerator

import httpx
from loguru import logger

from app.adapters.base import BaseAdapter, ModelInfo


class OpenAICompatibleAdapter(BaseAdapter):
    """
    通用 OpenAI 兼容适配器

    使用方式 — 每个模型只需传入配置即可:
        adapter = OpenAICompatibleAdapter(
            model_info=ModelInfo(model_id="deepseek-v4-pro", ...),
            api_key="sk-xxx",
            base_url="https://api.deepseek.com/v1",
        )
    """

    def __init__(
        self,
        model_info: ModelInfo,
        api_key: str,
        base_url: str,
        timeout: float = 120.0,
    ):
        self.model_info = model_info
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._chat_url = f"{self._base_url}/chat/completions"

    # ---- 非流式 ----

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int = 8192,
        **params,
    ) -> dict:
        body = self._build_body(messages, temperature, max_tokens, stream=False, **params)
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            logger.debug(f"[{self.model_info.model_id}] POST {self._chat_url}")
            response = await client.post(self._chat_url, json=body, headers=headers)
            if not response.is_success:
                detail = response.text[:500] if response.text else f"HTTP {response.status_code}"
                logger.error(f"[{self.model_info.model_id}] API error {response.status_code}: {detail}")
                raise RuntimeError(f"[{self.model_info.model_id}] API {response.status_code}: {detail}")
            return response.json()

    # ---- 流式 ----

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int = 8192,
        **params,
    ) -> AsyncGenerator[dict, None]:
        body = self._build_body(messages, temperature, max_tokens, stream=True, **params)
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            logger.debug(f"[{self.model_info.model_id}] SSE POST {self._chat_url}")
            async with client.stream("POST", self._chat_url, json=body, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_str)
                        choice = chunk.get("choices", [{}])[0]
                        yield {
                            "delta": choice.get("delta", {}),
                            "finish_reason": choice.get("finish_reason"),
                        }
                    except json.JSONDecodeError:
                        logger.warning(f"[{self.model_info.model_id}] 无法解析 SSE 行: {data_str}")
                        continue

    # ---- 内部方法 ----

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        messages: list[dict],
        temperature: float | None,
        max_tokens: int,
        stream: bool = False,
        **params,
    ) -> dict:
        body = {
            "model": self.model_info.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if temperature is not None:
            body["temperature"] = temperature

        # 深度思考/推理模式 — 各厂商参数格式不同
        thinking_enabled = params.pop("thinking", False)
        if thinking_enabled:
            pk = self.model_info.provider_key
            if pk == "qwen":
                body["enable_thinking"] = True
            elif pk in ("deepseek", "glm", "kimi", "doubao"):
                body["thinking"] = {"type": "enabled"}

        # 透传额外参数（如 top_p, enable_search 等）
        body.update(params)
        return body
