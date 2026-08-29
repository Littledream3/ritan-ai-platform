"""Redis 连接"""

import redis.asyncio as aioredis

from app.core.config import settings


async def get_redis() -> aioredis.Redis:
    """创建 Redis 连接"""
    return aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


# 模块级 Redis 客户端（在 lifespan 中初始化）
redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """应用启动时初始化 Redis 连接"""
    global redis_client
    redis_client = await get_redis()


async def close_redis() -> None:
    """应用关闭时释放 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def check_redis() -> bool:
    """健康检查 — 测试 Redis 连接"""
    try:
        if redis_client:
            return await redis_client.ping()
        return False
    except Exception:
        return False
