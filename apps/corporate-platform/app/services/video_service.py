"""视频生成服务 — 统一入口，根据 model 路由到 Qwen / GLM / Doubao

所有三家厂商均为异步模式：提交任务 → 轮询结果
"""

import asyncio
import time
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# ============================================================
# 视频模型注册表
# ============================================================

VIDEO_MODELS: dict[str, dict[str, Any]] = {
    "wan2.7-t2v": {
        "display_name": "通义万相 2.7 文生视频",
        "provider": "qwen",
        "description": "阿里通义万相最新视频生成模型，支持多镜头叙事",
        "resolutions": ["720P", "1080P"],
        "default_resolution": "720P",
        "ratios": ["16:9", "9:16", "1:1", "4:3", "3:4"],
        "durations": [2, 3, 4, 5, 6, 7, 8, 9, 10],
        "max_duration": 10,
    },
    "cogvideox-3": {
        "display_name": "CogVideoX 3",
        "provider": "glm",
        "description": "智谱最新视频生成模型，支持 4K 分辨率",
        "resolutions": ["1280x720", "720x1280", "1920x1080", "1080x1920"],
        "default_resolution": "1280x720",
        "ratios": ["16:9", "9:16", "1:1"],
        "durations": [5, 10],
        "max_duration": 10,
        "qualities": ["speed", "quality"],
        "fps_options": [30, 60],
    },
    "doubao-seedance-2-0-260128": {
        "display_name": "Seedance 2.0",
        "provider": "doubao",
        "description": "字节豆包最新视频生成模型，支持 4~15 秒",
        "resolutions": ["480p", "720p", "1080p"],
        "default_resolution": "720p",
        "ratios": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
        "durations": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "max_duration": 15,
    },
}

# 视频生成轮询配置（比图片轮询更久，因为视频生成耗时长）
POLL_MAX = 60        # 最多轮询 60 次
POLL_INTERVAL = 5    # 每次间隔 5 秒（共 300s = 5 分钟）


# ============================================================
# Qwen（通义万相）— 异步提交 + 轮询
# ============================================================

QWEN_VIDEO_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
QWEN_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"


async def _generate_qwen_video(
    model: str,
    prompt: str,
    resolution: str | None = None,
    ratio: str | None = None,
    duration: int = 5,
    watermark: bool = False,
    **kwargs,
) -> dict:
    """Qwen 通义万相视频生成 — 异步任务模式"""
    headers = {
        "Authorization": f"Bearer {settings.qwen_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    model_info = VIDEO_MODELS[model]
    params: dict[str, Any] = {
        "resolution": resolution or model_info["default_resolution"],
        "ratio": ratio or "16:9",
        "duration": duration,
        "prompt_extend": True,
        "watermark": watermark,
    }

    body: dict[str, Any] = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": params,
    }

    # 1. 提交任务
    async with httpx.AsyncClient(timeout=30) as client:
        logger.info(f"[video:qwen] 提交任务 model={model} resolution={params['resolution']} duration={duration}s")
        resp = await client.post(QWEN_VIDEO_URL, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "Qwen")

        result = resp.json()
        task_id = result.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Qwen 视频任务提交失败，未返回 task_id: {result}")

        logger.info(f"[video:qwen] 任务已提交 task_id={task_id}")

    # 2. 轮询结果
    return await _poll_qwen(task_id, headers, model)


async def _poll_qwen(task_id: str, headers: dict, model: str) -> dict:
    """轮询 Qwen 任务状态"""
    task_url = f"{QWEN_TASK_URL}/{task_id}"
    for attempt in range(1, POLL_MAX + 1):
        await asyncio.sleep(POLL_INTERVAL)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(task_url, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"[video:qwen] 轮询失败 (attempt {attempt}): HTTP {resp.status_code}")
                continue

            task = resp.json()
            output = task.get("output", {})
            status = output.get("task_status")

            if status == "SUCCEEDED":
                video_url = output.get("video_url")
                if not video_url:
                    raise RuntimeError("Qwen 视频任务完成但未返回 video_url")
                logger.info(f"[video:qwen] 生成成功 task_id={task_id}")
                return {
                    "model": model,
                    "created": int(time.time()),
                    "data": [{"url": video_url}],
                    "usage": task.get("usage", {}),
                }

            if status == "FAILED":
                err_msg = output.get("message", "未知错误")
                raise RuntimeError(f"Qwen 视频生成失败: {err_msg}")

            elapsed = attempt * POLL_INTERVAL
            logger.debug(f"[video:qwen] 轮询中... status={status} elapsed={elapsed}s")

    raise TimeoutError(f"Qwen 视频生成超时（已等待 {POLL_MAX * POLL_INTERVAL}s）")


# ============================================================
# GLM（CogVideoX）— 异步提交 + 轮询
# ============================================================

GLM_VIDEO_URL: str = ""  # 在函数内动态构建


async def _generate_glm_video(
    model: str,
    prompt: str,
    resolution: str | None = None,
    ratio: str | None = None,
    duration: int = 5,
    quality: str | None = None,
    fps: int | None = None,
    with_audio: bool = True,
    watermark: bool = False,
    **kwargs,
) -> dict:
    """GLM CogVideoX 视频生成 — 异步任务模式"""
    url = f"{settings.glm_base_url}/videos/generations"
    headers = {
        "Authorization": f"Bearer {settings.glm_api_key}",
        "Content-Type": "application/json",
    }

    model_info = VIDEO_MODELS[model]
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": resolution or model_info["default_resolution"],
        "duration": duration,
        "with_audio": with_audio,
        "watermark": watermark,
    }
    if quality:
        body["quality"] = quality
    if fps:
        body["fps"] = fps

    # 1. 提交任务
    async with httpx.AsyncClient(timeout=30) as client:
        logger.info(f"[video:glm] 提交任务 model={model} size={body['size']} duration={duration}s")
        resp = await client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "GLM")

        result = resp.json()
        task_id = result.get("id")
        if not task_id:
            raise RuntimeError(f"GLM 视频任务提交失败，未返回 id: {result}")

        logger.info(f"[video:glm] 任务已提交 id={task_id}")

    # 2. 轮询结果
    return await _poll_glm(task_id, headers, model)


async def _poll_glm(task_id: str, headers: dict, model: str) -> dict:
    """轮询 GLM 异步任务"""
    poll_url = f"{settings.glm_base_url}/async-result/{task_id}"
    for attempt in range(1, POLL_MAX + 1):
        await asyncio.sleep(POLL_INTERVAL)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(poll_url, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"[video:glm] 轮询失败 (attempt {attempt}): HTTP {resp.status_code}")
                continue

            result = resp.json()
            task_status = result.get("task_status")

            if task_status == "SUCCESS":
                video_url = result.get("video_url")
                if not video_url:
                    raise RuntimeError("GLM 视频任务完成但未返回 video_url")
                logger.info(f"[video:glm] 生成成功 id={task_id}")
                return {
                    "model": model,
                    "created": int(time.time()),
                    "data": [{"url": video_url}],
                    "usage": result.get("usage", {}),
                }

            if task_status == "FAIL":
                err_msg = result.get("message", str(result))
                raise RuntimeError(f"GLM 视频生成失败: {err_msg}")

            elapsed = attempt * POLL_INTERVAL
            logger.debug(f"[video:glm] 轮询中... status={task_status} elapsed={elapsed}s")

    raise TimeoutError(f"GLM 视频生成超时（已等待 {POLL_MAX * POLL_INTERVAL}s）")


# ============================================================
# Doubao（Seedance）— 异步提交 + 轮询
# ============================================================


async def _generate_doubao_video(
    model: str,
    prompt: str,
    resolution: str | None = None,
    ratio: str | None = None,
    duration: int = 5,
    watermark: bool = False,
    **kwargs,
) -> dict:
    """Doubao Seedance 视频生成 — 异步任务模式"""
    url = f"{settings.doubao_base_url}/contents/generations/tasks"
    headers = {
        "Authorization": f"Bearer {settings.doubao_api_key}",
        "Content-Type": "application/json",
    }

    model_info = VIDEO_MODELS[model]
    body: dict[str, Any] = {
        "model": model,
        "content": [
            {"type": "text", "text": prompt}
        ],
        "resolution": resolution or model_info["default_resolution"],
        "ratio": ratio or "16:9",
        "duration": duration,
        "watermark": watermark,
    }

    # 1. 提交任务
    async with httpx.AsyncClient(timeout=30) as client:
        logger.info(f"[video:doubao] 提交任务 model={model} resolution={body['resolution']} duration={duration}s")
        resp = await client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            _raise_detail(resp, "Doubao")

        result = resp.json()
        task_id = result.get("id")
        if not task_id:
            raise RuntimeError(f"Doubao 视频任务提交失败，未返回 id: {result}")

        logger.info(f"[video:doubao] 任务已提交 id={task_id}")

    # 2. 轮询结果
    return await _poll_doubao(task_id, headers, model)


async def _poll_doubao(task_id: str, headers: dict, model: str) -> dict:
    """轮询 Doubao 任务状态"""
    poll_url = f"{settings.doubao_base_url}/contents/generations/tasks/{task_id}"
    for attempt in range(1, POLL_MAX + 1):
        await asyncio.sleep(POLL_INTERVAL)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(poll_url, headers=headers)

            if resp.status_code != 200:
                logger.warning(f"[video:doubao] 轮询失败 (attempt {attempt}): HTTP {resp.status_code}")
                continue

            result = resp.json()
            status = result.get("status")

            if status == "succeeded":
                video_url = result.get("content", {}).get("video_url")
                if not video_url:
                    # 尝试其他可能的字段
                    video_url = result.get("video_url")
                if not video_url:
                    raise RuntimeError("Doubao 视频任务完成但未返回 video_url")
                logger.info(f"[video:doubao] 生成成功 id={task_id}")
                return {
                    "model": model,
                    "created": int(time.time()),
                    "data": [{"url": video_url}],
                    "usage": result.get("usage", {}),
                    "resolution": result.get("resolution"),
                    "duration": result.get("duration"),
                }

            if status == "failed":
                err_msg = result.get("error", {}).get("message", str(result))
                raise RuntimeError(f"Doubao 视频生成失败: {err_msg}")

            elapsed = attempt * POLL_INTERVAL
            logger.debug(f"[video:doubao] 轮询中... status={status} elapsed={elapsed}s")

    raise TimeoutError(f"Doubao 视频生成超时（已等待 {POLL_MAX * POLL_INTERVAL}s）")


# ============================================================
# 统一入口
# ============================================================

PROVIDER_HANDLERS = {
    "qwen": _generate_qwen_video,
    "glm": _generate_glm_video,
    "doubao": _generate_doubao_video,
}


async def generate_video(
    model: str,
    prompt: str,
    resolution: str | None = None,
    ratio: str | None = None,
    duration: int = 5,
    quality: str | None = None,
    fps: int | None = None,
    with_audio: bool = True,
    watermark: bool = False,
    **kwargs,
) -> dict:
    """统一文生视频入口 — 根据 model 路由到对应厂商

    Returns:
        {"model": "...", "created": 1234567890, "data": [{"url": "..."}]}
    """
    model_info = VIDEO_MODELS.get(model)
    if model_info is None:
        available = ", ".join(VIDEO_MODELS.keys())
        raise ValueError(f"模型 '{model}' 不支持视频生成，可用: {available}")

    provider = model_info["provider"]
    handler = PROVIDER_HANDLERS.get(provider)
    if handler is None:
        raise ValueError(f"厂商 '{provider}' 暂不支持视频生成")

    return await handler(
        model=model,
        prompt=prompt,
        resolution=resolution,
        ratio=ratio,
        duration=duration,
        quality=quality,
        fps=fps,
        with_audio=with_audio,
        watermark=watermark,
        **kwargs,
    )


def get_available_video_models() -> list[dict]:
    """返回所有视频模型及其可用状态（用于 /videos/models 接口）"""
    models = []
    for model_id, info in VIDEO_MODELS.items():
        provider = info["provider"]
        available = _check_api_key(provider)
        models.append({
            "model_id": model_id,
            "display_name": info["display_name"],
            "provider": info["provider"],
            "description": info["description"],
            "available": available,
            "resolutions": info["resolutions"],
            "default_resolution": info["default_resolution"],
            "ratios": info["ratios"],
            "max_duration": info["max_duration"],
            "durations": info["durations"],
            "qualities": info.get("qualities"),
            "fps_options": info.get("fps_options"),
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
    logger.error(f"[video:{provider.lower()}] HTTP {resp.status_code}: {detail}")
    raise RuntimeError(f"{provider} API 错误 ({resp.status_code}): {detail}")
