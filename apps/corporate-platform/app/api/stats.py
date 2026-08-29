"""用量统计 API — 用户查询自己的用量"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.stats_service import (
    get_user_history,
    get_user_today_by_model,
    get_user_today_stats,
)

router = APIRouter(prefix="/api/v1/stats", tags=["用量统计"])


@router.get("/today")
async def today_stats(user: User = Depends(get_current_user)):
    """今日用量汇总 + 各模型明细（Redis 实时）"""
    summary = await get_user_today_stats(user.id)
    by_model = await get_user_today_by_model(user.id)
    return {
        "user_id": user.id,
        "summary": summary,
        "by_model": by_model,
    }


@router.get("/history")
async def history(
    model: str | None = Query(default=None, description="按模型筛选"),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """历史用量明细（MySQL 分页）"""
    rows, total = await get_user_history(
        db,
        user_id=user.id,
        model=model,
        days=days,
        limit=limit,
        offset=offset,
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "latency_ms": r.latency_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
