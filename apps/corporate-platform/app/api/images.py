"""图片生成 API"""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.image import ImageGenerationRequest
from app.services.image_service import generate_image, get_available_image_models

router = APIRouter(prefix="/api/v1", tags=["图片生成"])


@router.get("/images/models")
async def list_image_models():
    """返回可用的图片生成模型列表"""
    models = get_available_image_models()
    return {"models": models}


@router.post("/images/generate")
async def create_image(
    body: ImageGenerationRequest,
    user: User = Depends(get_current_user),
):
    """文生图 — 根据 model 路由到对应厂商（Qwen / GLM / Doubao）"""
    # 1. 校验模型是否支持图片生成
    models = {m["model_id"]: m for m in get_available_image_models()}
    model_info = models.get(body.model)

    if model_info is None:
        available = ", ".join(models.keys()) or "无"
        raise HTTPException(
            status_code=400,
            detail=f"模型 '{body.model}' 不支持图片生成，可用: {available}",
        )

    # 2. 校验 API Key 是否配置
    if not model_info["available"]:
        raise HTTPException(
            status_code=503,
            detail=f"图片生成模型 '{body.model}' 不可用（API Key 未配置）",
        )

    # 3. 调用图片生成服务
    logger.info(
        f"📸 用户 {user.username} 请求图片生成 model={body.model} "
        f"size={body.size or model_info['default_size']} "
        f"prompt={body.prompt[:50]}..."
    )

    try:
        result = await generate_image(
            model=body.model,
            prompt=body.prompt,
            size=body.size,
            n=body.n,
            quality=body.quality,
            response_format=body.response_format,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"图片生成未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"图片生成失败: {e}")
