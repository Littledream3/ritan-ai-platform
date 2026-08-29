"""管理后台 API — 需 admin 角色"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_admin_user
from app.models.user import User, UserRole
from app.models.usage_log import UsageLog
from app.schemas.user import UserInfo
from app.services.stats_service import get_global_stats

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])


# ---- 统计概览 ----

@router.get("/stats")
async def admin_stats(
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """全局统计概览 — 总调用量、Token 消耗、活跃用户、各模型占比"""
    return await get_global_stats(db, days=days)


# ---- 用量日志 ----

@router.get("/logs")
async def admin_logs(
    model: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """全平台用量明细（分页 + 筛选）"""
    from datetime import datetime, timedelta

    conditions = []
    if model:
        conditions.append(UsageLog.model == model)
    if user_id:
        conditions.append(UsageLog.user_id == user_id)
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        conditions.append(UsageLog.created_at >= since)

    # 总数
    count_q = select(func.count(UsageLog.id)).where(*conditions)
    total = (await db.execute(count_q)).scalar() or 0

    # 分页查询（join user 获取用户名）
    q = (
        select(UsageLog, User.username)
        .join(User, UsageLog.user_id == User.id)
        .where(*conditions)
        .order_by(UsageLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(q)).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": username,
                "model": log.model,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat(),
            }
            for log, username in rows
        ],
    }


# ---- 用户管理 ----

@router.get("/users")
async def admin_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """用户列表"""
    count_q = select(func.count(User.id))
    total = (await db.execute(count_q)).scalar() or 0

    q = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    users = (await db.execute(q)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [UserInfo.model_validate(u).model_dump() for u in users],
    }


class EditUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    name: str | None = None


@router.put("/users/{user_id}")
async def admin_edit_user(
    user_id: int,
    body: EditUserRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑用户 — 角色 / 启用状态 / 名称"""
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.role is not None:
        if body.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="角色只能是 admin 或 user")
        target.role = UserRole(body.role)

    if body.is_active is not None:
        target.is_active = body.is_active

    if body.name is not None:
        target.name = body.name

    await db.flush()
    await db.refresh(target)
    return UserInfo.model_validate(target)
