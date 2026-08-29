"""认证 API — 注册 + 登录 + 个人信息"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.user import TokenResponse, UserInfo
from app.services.auth_service import (
    create_jwt,
    generate_and_send_code,
    login_user,
    register_user,
    reset_password,
    send_reset_code,
    verify_code,
)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


# ---- 请求体 ----

class SendCodeRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str = ""
    email: str = ""
    code: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


# ---- 端点 ----

@router.post("/send-code")
async def send_code(body: SendCodeRequest):
    """发送邮箱验证码"""
    email = body.email.strip()

    # 校验邮箱格式：必须是 contact@example.invalid
    if not email.endswith("@ritanai.com") or email == "@ritanai.com" or email.count("@") != 1:
        raise HTTPException(status_code=400, detail="邮箱格式错误，请使用 contact@example.invalid")

    try:
        result = await generate_and_send_code(email)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新账号（需邮箱验证码）"""
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    # 校验邮箱格式
    email = body.email.strip()
    if not email or not email.endswith("@ritanai.com") or email == "@ritanai.com" or email.count("@") != 1:
        raise HTTPException(status_code=400, detail="邮箱格式错误，请使用 contact@example.invalid")

    # 校验验证码格式
    if not body.code or not body.code.isdigit() or len(body.code) != 6:
        raise HTTPException(status_code=400, detail="请提供 6 位验证码")

    # 验证验证码
    try:
        await verify_code(email, body.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        user = await register_user(db, body.username, body.password, body.name, email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = create_jwt(user)
    return TokenResponse(access_token=token, user=UserInfo.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """账号密码登录"""
    try:
        user = await login_user(db, body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    token = create_jwt(user)
    return TokenResponse(access_token=token, user=UserInfo.model_validate(user))


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserInfo.model_validate(user)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """发送密码重置验证码"""
    email = body.email.strip()
    if not email.endswith("@ritanai.com") or email == "@ritanai.com" or email.count("@") != 1:
        raise HTTPException(status_code=400, detail="邮箱格式错误，请使用 contact@example.invalid")

    try:
        result = await send_reset_code(email)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@router.post("/reset-password")
async def reset_password_endpoint(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """重置密码"""
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    email = body.email.strip()
    if not email.endswith("@ritanai.com") or email == "@ritanai.com" or email.count("@") != 1:
        raise HTTPException(status_code=400, detail="邮箱格式错误，请使用 contact@example.invalid")

    if not body.code or not body.code.isdigit() or len(body.code) != 6:
        raise HTTPException(status_code=400, detail="请提供 6 位验证码")

    try:
        result = await reset_password(db, email, body.code, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result
