"""图片生成服务 — 统一入口，根据 model 路由到 Qwen / GLM / Doubao"""

import asyncio
import time
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# ============================================================
# 图片模型注册表（与 Chat 模型独立）
# ============================================================

IMAGE_MODELS: dict[str, dict[str, Any]] = {
    "wanx2.1-t2i-turbo": {
        "display_name": "通义万相 2.1 Turbo",
        "provider": "qwen",
        "description": "阿里通义万相快速文生图",
        "sizes": ["1024*1024", "720*1280", "1280*720", "1664*928"],
        "default_size": "1024*1024",
    },
    "cogview-4-250304": {
        "display_name": "CogView 4",
        "provider": "glm",
        "description": "智谱最新文生图模型，支持中文文字渲染",
        "sizes": [
            "1024x1024", "768x1344", "864x1152",
            "1344x768", "1152x864", "1440x720", "720x1440",
        ],
        "default_size": "1024x1024",
        "qualities": ["standard", "hd"],
    },
    "doubao-seedream-5-0-260128": {
        "display_name": "Seedream 5.0 Lite",
        "provider": "doubao",
        "description": "字节豆包最新文生图模型，支持 2K/3K/4K",
        "sizes": ["2K", "3K", "4K"],
        "default_size": "2K",
        "formats": ["png", "jpeg"],
    },
}

# ============================================================
# Qwen（通义万相）— 异步提交 + 轮询
# ============================================================

QWEN_IMAGE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
QWEN_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"
QWEN_POLL_MAX = 30       # 最多轮询 30 次
QWEN_POLL_INTERVAL = 2   # 每次间隔 2 秒


async def _generate_qwen(
    model: str,
    prompt: str,
    size: str | None = None,
    n: int = 1,
    **kwargs,
) -> dict:
    """Qwen 通义万相 — 异步任务模式"""
    headers = {
        "Authorization": f"Bearer {settings.qwen_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    body: dict[str, Any] = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "size": size or IMAGE_MODELS[model]["default_size"],
            "n": n,
            "prompt_extend": True,
            "watermark": False,
        },
    }

    # 1. 提交任务
    async with httpx.AsyncClient(timeout=30) as client:
        logger.info(f"[image:qwen] 提交任务 model={model} size={size}")
        resp = await client.post(QWEN_IMAGE_URL, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "Qwen")

        result = resp.json()
        task_id = result.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Qwen 任务提交失败，未返回 task_id: {result}")

        logger.info(f"[image:qwen] 任务已提交 task_id={task_id}")

    # 2. 轮询结果
    task_url = f"{QWEN_TASK_URL}/{task_id}"
    for attempt in range(1, QWEN_POLL_MAX + 1):
        await asyncio.sleep(QWEN_POLL_INTERVAL)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(task_url, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"[image:qwen] 轮询失败 (attempt {attempt}): HTTP {resp.status_code}")
                continue

            task = resp.json()
            status = task.get("output", {}).get("task_status")

            if status == "SUCCEEDED":
                results = task.get("output", {}).get("results", [])
                urls = []
                for r in results:
                    if r.get("url"):
                        urls.append({"url": r["url"]})
                if not urls:
                    raise RuntimeError("Qwen 任务完成但未返回图片 URL")
                logger.info(f"[image:qwen] 生成成功 task_id={task_id} images={len(urls)}")
                return {
                    "model": model,
                    "created": int(time.time()),
                    "data": urls,
                }

            if status == "FAILED":
                err_msg = task.get("output", {}).get("message", "未知错误")
                raise RuntimeError(f"Qwen 图片生成失败: {err_msg}")

            logger.debug(f"[image:qwen] 轮询中... status={status} attempt={attempt}")

    raise TimeoutError(f"Qwen 图片生成超时（已等待 {QWEN_POLL_MAX * QWEN_POLL_INTERVAL}s）")


# ============================================================
# GLM（CogView）— 同步请求
# ============================================================


async def _generate_glm(
    model: str,
    prompt: str,
    size: str | None = None,
    n: int = 1,
    quality: str | None = None,
    **kwargs,
) -> dict:
    """GLM CogView — 同步模式"""
    url = f"{settings.glm_base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.glm_api_key}",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    if size:
        body["size"] = size
    if quality:
        body["quality"] = quality

    async with httpx.AsyncClient(timeout=120) as client:
        logger.info(f"[image:glm] 请求生成 model={model} size={size}")
        resp = await client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "GLM")

        result = resp.json()
        logger.info(f"[image:glm] 生成成功 images={len(result.get('data', []))}")

        # GLM 一次只返回一张图片，这里兼容 n > 1 时多次调用
        return {
            "model": model,
            "created": result.get("created", int(time.time())),
            "data": result.get("data", []),
        }


# ============================================================
# Doubao（Seedream）— 同步请求
# ============================================================


async def _generate_doubao(
    model: str,
    prompt: str,
    size: str | None = None,
    n: int = 1,
    response_format: str = "url",
    **kwargs,
) -> dict:
    """Doubao Seedream — 同步模式"""
    url = f"{settings.doubao_base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.doubao_api_key}",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": size or IMAGE_MODELS[model]["default_size"],
        "response_format": response_format,
        "watermark": False,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        logger.info(f"[image:doubao] 请求生成 model={model} size={size}")
        resp = await client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "Doubao")

        result = resp.json()
        logger.info(f"[image:doubao] 生成成功 images={len(result.get('data', []))}")

        return {
            "model": model,
            "created": result.get("created", int(time.time())),
            "data": result.get("data", []),
        }


# ============================================================
# 统一入口
# ============================================================

PROVIDER_HANDLERS = {
    "qwen": _generate_qwen,
    "glm": _generate_glm,
    "doubao": _generate_doubao,
}


async def generate_image(
    model: str,
    prompt: str,
    size: str | None = None,
    n: int = 1,
    quality: str | None = None,
    response_format: str = "url",
    **kwargs,
) -> dict:
    """统一文生图入口 — 根据 model 路由到对应厂商

    Returns:
        {"model": "...", "created": 1234567890, "data": [{"url": "..."}]}
    """
    model_info = IMAGE_MODELS.get(model)
    if model_info is None:
        available = ", ".join(IMAGE_MODELS.keys())
        raise ValueError(f"模型 '{model}' 不支持图片生成，可用: {available}")

    provider = model_info["provider"]
    handler = PROVIDER_HANDLERS.get(provider)
    if handler is None:
        raise ValueError(f"厂商 '{provider}' 暂不支持图片生成")

    return await handler(
        model=model,
        prompt=prompt,
        size=size,
        n=n,
        quality=quality,
        response_format=response_format,
        **kwargs,
    )


def get_available_image_models() -> list[dict]:
    """返回所有图片模型及其可用状态（用于 /images/models 接口）"""
    models = []
    for model_id, info in IMAGE_MODELS.items():
        # 检查对应厂商的 API Key 是否配置
        provider = info["provider"]
        available = _check_api_key(provider)
        models.append({
            "model_id": model_id,
            "display_name": info["display_name"],
            "provider": info["provider"],
            "description": info["description"],
            "available": available,
            "sizes": info["sizes"],
            "default_size": info["default_size"],
            "qualities": info.get("qualities"),
            "formats": info.get("formats"),
        })
    return models


def _check_api_key(provider: str) -> bool:
    """检查指定厂商的 API Key 是否已配置"""
    key_map = {
        "qwen": settings.qwen_api_key,
        "glm": settings.glm_api_key,
        "doubao": settings.doubao_api_key,
    }
    key = key_map.get(provider, "")
    return bool(key) and key not in ("", "your_api_key_here")


def _raise_detail(resp: httpx.Response, provider: str) -> None:
    """解析厂商错误响应并抛出"""
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text
    logger.error(f"[image:{provider.lower()}] HTTP {resp.status_code}: {detail}")
    raise RuntimeError(f"{provider} API 错误 ({resp.status_code}): {detail}")
