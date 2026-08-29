"""视频生成 API"""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.video import VideoGenerationRequest
from app.services.video_service import generate_video, get_available_video_models

router = APIRouter(prefix="/api/v1", tags=["视频生成"])


@router.get("/videos/models")
async def list_video_models():
    """返回可用的视频生成模型列表"""
    models = get_available_video_models()
    return {"models": models}


@router.post("/videos/generate")
async def create_video(
    body: VideoGenerationRequest,
    user: User = Depends(get_current_user),
):
    """文生视频 — 根据 model 路由到对应厂商（Qwen / GLM / Doubao）

    所有厂商均为异步模式：提交任务后轮询等待完成（最长 5 分钟）。
    """
    # 1. 校验模型是否支持视频生成
    models = {m["model_id"]: m for m in get_available_video_models()}
    model_info = models.get(body.model)

    if model_info is None:
        available = ", ".join(models.keys()) or "无"
        raise HTTPException(
            status_code=400,
            detail=f"模型 '{body.model}' 不支持视频生成，可用: {available}",
        )

    # 2. 校验 API Key 是否配置
    if not model_info["available"]:
        raise HTTPException(
            status_code=503,
            detail=f"视频生成模型 '{body.model}' 不可用（API Key 未配置）",
        )

    # 3. 调用视频生成服务
    logger.info(
        f"🎬 用户 {user.username} 请求视频生成 model={body.model} "
        f"resolution={body.resolution or model_info['default_resolution']} "
        f"duration={body.duration}s "
        f"prompt={body.prompt[:50]}..."
    )

    try:
        result = await generate_video(
            model=body.model,
            prompt=body.prompt,
            resolution=body.resolution,
            ratio=body.ratio,
            duration=body.duration,
            quality=body.quality,
            fps=body.fps,
            with_audio=body.with_audio,
            watermark=body.watermark,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"视频生成未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"视频生成失败: {e}")
