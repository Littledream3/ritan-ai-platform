"""认证服务 — 账号密码登录 + JWT + 邮箱验证码"""

import hashlib
import hmac
import os
import random
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_module
from app.core.config import settings
from app.models.user import User, UserRole
from app.services.email_service import send_password_reset_email, send_verification_email

# 验证码 Redis Key 前缀
CODE_PREFIX = "verify_code:"
RATE_LIMIT_PREFIX = "send_count:"
CODE_TTL = 300       # 5 分钟
RATE_TTL = 3600      # 1 小时
MAX_SEND_COUNT = 3

# PBKDF2 参数
HASH_ITERATIONS = 600_000
HASH_ALGORITHM = "sha256"
SALT_LENGTH = 32


def hash_password(password: str) -> str:
    """PBKDF2 哈希密码，返回格式: $pbkdf2$<iterations>$<salt_hex>$<hash_hex>"""
    salt = os.urandom(SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode(), salt, HASH_ITERATIONS)
    return f"$pbkdf2${HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    try:
        _, algo, iterations, salt_hex, hash_hex = hashed.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac(HASH_ALGORITHM, plain.encode(), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, AttributeError):
        return False


async def register_user(
    db: AsyncSession,
    username: str,
    password: str,
    name: str = "",
    email: str = None,
) -> User:
    """注册新用户"""
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise ValueError(f"用户名 '{username}' 已存在")

    # 检查邮箱唯一性
    if email:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError(f"邮箱 '{email}' 已被注册")

    user = User(
        username=username,
        password_hash=hash_password(password),
        name=name or username,
        email=email,
        role=UserRole.user,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)  # 加载 server_default 生成的字段（如 created_at）
    return user


async def login_user(db: AsyncSession, username: str, password: str) -> User:
    """用户名密码登录"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")

    if not user.is_active:
        raise ValueError("账号已被禁用")

    return user


def create_jwt(user: User) -> str:
    """为用户签发 JWT"""
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict:
    """解析 JWT，失败抛异常"""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ---- 邮箱验证码 ----


async def generate_and_send_code(email: str) -> dict:
    """生成验证码并发送邮件，返回状态信息"""
    # 1. 检查发送频率限制
    count_key = f"{RATE_LIMIT_PREFIX}{email}"
    current_count = await redis_module.redis_client.get(count_key)
    if current_count and int(current_count) >= MAX_SEND_COUNT:
        raise ValueError("该邮箱验证码发送次数已达上限，请 1 小时后再试")

    # 2. 生成 6 位随机验证码
    code = f"{random.randint(0, 999999):06d}"

    # 3. 存入 Redis，5 分钟过期
    code_key = f"{CODE_PREFIX}{email}"
    await redis_module.redis_client.set(code_key, code, ex=CODE_TTL)

    # 4. 递增发送计数（原子操作）
    pipe = redis_module.redis_client.pipeline()
    pipe.incr(count_key)
    pipe.expire(count_key, RATE_TTL)
    await pipe.execute()

    # 5. 发送邮件
    success = await send_verification_email(email, code)
    if not success:
        raise RuntimeError("验证码发送失败，请稍后重试")

    return {"message": "验证码已发送"}


async def verify_code(email: str, code: str) -> bool:
    """校验验证码，成功后删除 Redis 中的 code"""
    code_key = f"{CODE_PREFIX}{email}"
    stored_code = await redis_module.redis_client.get(code_key)
    if stored_code is None:
        raise ValueError("验证码已过期或未发送")
    if stored_code != code:
        raise ValueError("验证码错误")
    # 消费验证码（一次性使用）
    await redis_module.redis_client.delete(code_key)
    return True


# ---- 密码重置 ----

RESET_CODE_PREFIX = "reset_code:"
RESET_RATE_PREFIX = "reset_count:"


async def send_reset_code(email: str) -> dict:
    """发送密码重置验证码"""
    # 1. 检查发送频率
    count_key = f"{RESET_RATE_PREFIX}{email}"
    current_count = await redis_module.redis_client.get(count_key)
    if current_count and int(current_count) >= MAX_SEND_COUNT:
        raise ValueError("该邮箱重置密码请求次数已达上限，请 1 小时后再试")

    # 2. 生成 6 位验证码
    code = f"{random.randint(0, 999999):06d}"

    # 3. 存入 Redis，5 分钟过期
    code_key = f"{RESET_CODE_PREFIX}{email}"
    await redis_module.redis_client.set(code_key, code, ex=CODE_TTL)

    # 4. 递增发送计数
    pipe = redis_module.redis_client.pipeline()
    pipe.incr(count_key)
    pipe.expire(count_key, RATE_TTL)
    await pipe.execute()

    # 5. 发送邮件
    success = await send_password_reset_email(email, code)
    if not success:
        raise RuntimeError("验证码发送失败，请稍后重试")

    return {"message": "密码重置验证码已发送"}


async def reset_password(
    db: AsyncSession,
    email: str,
    code: str,
    new_password: str,
) -> dict:
    """验证重置码并更新密码"""
    # 1. 校验验证码
    code_key = f"{RESET_CODE_PREFIX}{email}"
    stored_code = await redis_module.redis_client.get(code_key)
    if stored_code is None:
        raise ValueError("验证码已过期或未发送")
    if stored_code != code:
        raise ValueError("验证码错误")
    await redis_module.redis_client.delete(code_key)

    # 2. 查找用户
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("该邮箱未注册")

    # 3. 更新密码
    user.password_hash = hash_password(new_password)
    await db.flush()

    return {"message": "密码已重置，请使用新密码登录"}
