"""多模型 API 网关 — FastAPI 入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.adapters.registry import registry
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.discuss import router as discuss_router
from app.api.export import router as export_router
from app.api.feishu import router as feishu_router
from app.api.images import router as images_router
from app.api.stats import router as stats_router
from app.api.upload import router as upload_router
from app.api.videos import router as videos_router
from app.core.config import settings
from app.core.database import check_database
from app.core.redis import check_redis, close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动中...")

    # 初始化 Redis
    await init_redis()
    logger.info("✅ Redis 已连接")

    # 测试数据库
    db_ok = await check_database()
    if db_ok:
        logger.info("✅ MySQL 已连接")
    else:
        logger.warning("⚠️ MySQL 连接失败")

    # 注册模型适配器
    registry.init()

    yield

    # 关闭资源
    await close_redis()
    logger.info("👋 服务已关闭")


app = FastAPI(
    title="多模型 API 网关",
    description="统一代理 DeepSeek / Kimi / Qwen / GLM / 豆包 五个大模型",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许管理后台跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义 422 处理器 — 不返回整个请求体（避免大请求导致巨大响应）
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        # 移除错误中的 input 字段（即请求体），只保留定位信息
        clean = {k: v for k, v in err.items() if k != "input"}
        errors.append(clean)
    logger.warning(f"请求验证失败: {request.url.path} — {len(errors)} validation errors")
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )

# 注册路由
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(discuss_router)
app.include_router(export_router)
app.include_router(feishu_router)
app.include_router(images_router)
app.include_router(videos_router)
app.include_router(stats_router)
app.include_router(upload_router)
app.include_router(admin_router)

# 管理后台静态资源（仅当已构建时挂载）
import os
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
_assets_dir = os.path.join(_static_dir, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/admin/assets", StaticFiles(directory=_assets_dir), name="admin_assets")

# 视频静态资源
_videos_dir = os.path.join(_static_dir, "videos")
os.makedirs(_videos_dir, exist_ok=True)
app.mount("/static/videos", StaticFiles(directory=_videos_dir), name="videos")


# ---- SPA 回退 ----

@app.get("/admin")
@app.get("/admin/{path:path}")
async def admin_spa(path: str = ""):
    """管理后台 SPA 入口 — 所有 /admin/* 返回 index.html"""
    index_path = os.path.join(_static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "管理后台尚未构建，请先执行 npm run build", "path": path}


# ---- 内置路由 ----

@app.get("/api/v1/health")
async def health():
    """健康检查"""
    db_ok = await check_database()
    redis_ok = await check_redis()
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": db_ok,
        "redis": redis_ok,
    }


@app.get("/api/v1/models")
async def list_models():
    """已注册的模型列表"""
    return {"models": registry.list_models()}
