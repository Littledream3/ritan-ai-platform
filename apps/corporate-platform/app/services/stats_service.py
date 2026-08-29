"""用量统计服务 — Redis 实时计数 + MySQL 持久查询"""

from datetime import date

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.redis as _redis
from app.models.usage_log import UsageLog


def _get_redis():
    """获取当前 Redis 客户端（运行时动态获取，避免模块导入时捕获 None）"""
    return _redis.redis_client


# Redis Key 前缀
KEY_PREFIX = "port:usage"
TTL_DAYS = 30  # Redis 数据保留 30 天


# ---- Redis 实时计数 ----

def _usage_key(user_id: int, model: str, day: str) -> str:
    return f"{KEY_PREFIX}:{user_id}:{model}:{day}"


def _total_key(user_id: int, day: str) -> str:
    return f"{KEY_PREFIX}:{user_id}:all:{day}"


async def record_chat(
    user_id: int,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """每次大模型调用后，Redis 实时计数 +1"""
    r = _get_redis()
    if r is None:
        return

    today = date.today().isoformat()
    model_key = _usage_key(user_id, model, today)
    total_key = _total_key(user_id, today)
    ttl = 60 * 60 * 24 * TTL_DAYS

    try:
        # 按模型维度
        await r.hincrby(model_key, "calls", 1)
        await r.hincrby(model_key, "prompt_tokens", prompt_tokens)
        await r.hincrby(model_key, "completion_tokens", completion_tokens)
        await r.expire(model_key, ttl)

        # 用户当日汇总
        await r.hincrby(total_key, "calls", 1)
        await r.hincrby(total_key, "prompt_tokens", prompt_tokens)
        await r.hincrby(total_key, "completion_tokens", completion_tokens)
        await r.expire(total_key, ttl)
    except Exception as e:
        logger.warning(f"Redis 统计记录失败: {e}")


async def get_user_today_stats(user_id: int) -> dict:
    """查询某用户今日实时用量（Redis）"""
    r = _get_redis()
    if r is None:
        return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    today = date.today().isoformat()
    total_key = _total_key(user_id, today)

    try:
        data = await r.hgetall(total_key)
        return {
            "calls": int(data.get("calls", 0)),
            "prompt_tokens": int(data.get("prompt_tokens", 0)),
            "completion_tokens": int(data.get("completion_tokens", 0)),
        }
    except Exception as e:
        logger.warning(f"Redis 查询失败: {e}")
        return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


async def get_user_today_by_model(user_id: int) -> list[dict]:
    """查询某用户今日各模型用量（Redis）"""
    r = _get_redis()
    if r is None:
        return []

    today = date.today().isoformat()
    pattern = _usage_key(user_id, "*", today)

    try:
        result = []
        async for key in r.scan_iter(match=pattern, count=10):
            data = await r.hgetall(key)
            parts = key.split(":")
            model = parts[-2] if len(parts) >= 5 else "unknown"
            if model == "all":
                continue  # 跳过汇总 key
            result.append({
                "model": model,
                "calls": int(data.get("calls", 0)),
                "prompt_tokens": int(data.get("prompt_tokens", 0)),
                "completion_tokens": int(data.get("completion_tokens", 0)),
            })
        return result
    except Exception as e:
        logger.warning(f"Redis 按模型查询失败: {e}")
        return []


# ---- MySQL 历史查询 ----

async def get_user_history(
    db: AsyncSession,
    user_id: int,
    model: str | None = None,
    days: int = 7,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[UsageLog], int]:
    """查询用户历史用量明细（MySQL），支持按模型筛选，分页"""
    from datetime import datetime, timedelta

    conditions = [UsageLog.user_id == user_id]
    if model:
        conditions.append(UsageLog.model == model)
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        conditions.append(UsageLog.created_at >= since)

    # 总数
    count_q = select(func.count(UsageLog.id)).where(*conditions)
    total = (await db.execute(count_q)).scalar() or 0

    # 分页查询
    q = (
        select(UsageLog)
        .where(*conditions)
        .order_by(UsageLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(q)).scalars().all()

    return list(rows), total


async def get_global_stats(db: AsyncSession, days: int = 7) -> dict:
    """全局统计概览 — 总调用量、各模型占比、活跃用户"""
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(days=days)

    # 总调用量
    total_q = select(func.count(UsageLog.id)).where(UsageLog.created_at >= since)
    total_calls = (await db.execute(total_q)).scalar() or 0

    # 总 token 消耗
    tokens_q = select(
        func.sum(UsageLog.prompt_tokens),
        func.sum(UsageLog.completion_tokens),
    ).where(UsageLog.created_at >= since)
    prompt_sum, completion_sum = (await db.execute(tokens_q)).one()

    # 活跃用户数
    user_q = select(func.count(func.distinct(UsageLog.user_id))).where(
        UsageLog.created_at >= since
    )
    active_users = (await db.execute(user_q)).scalar() or 0

    # 各模型调用量
    model_q = (
        select(UsageLog.model, func.count(UsageLog.id))
        .where(UsageLog.created_at >= since)
        .group_by(UsageLog.model)
    )
    model_rows = (await db.execute(model_q)).all()

    return {
        "period_days": days,
        "total_calls": total_calls,
        "total_prompt_tokens": prompt_sum or 0,
        "total_completion_tokens": completion_sum or 0,
        "active_users": active_users,
        "by_model": [{"model": m, "calls": c} for m, c in model_rows],
    }
