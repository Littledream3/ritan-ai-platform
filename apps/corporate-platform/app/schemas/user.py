"""用户相关 Pydantic Schema"""

from datetime import datetime

from pydantic import BaseModel


class UserInfo(BaseModel):
    """返回给前端的用户信息"""
    id: int
    username: str
    email: str | None = None
    name: str
    avatar: str | None = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录成功后返回的 JWT"""
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
