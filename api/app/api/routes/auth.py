
"""认证路由：注册 / 登录 / 当前用户。

端点（挂在 /api/v1/auth 前缀下）：
    - POST /auth/register   开放注册（普通用户）
    - POST /auth/login      登录，签发 JWT
    - GET  /auth/me         当前登录用户信息（需 token）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.config import get_settings
from app.models.schemas import (
    APIResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserInfo,
)
from app.security import create_access_token
from app.service.user_service import (
    User,
    authenticate,
    create_user,
    get_user_by_username,
)
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger("api.routes.auth")

_USERNAME_MIN = 3
_USERNAME_MAX = 32
_PASSWORD_MIN = 6


@router.post(
    "/register",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="用户注册",
    description="创建普通用户账号，成功后可直接登录。",
)
async def register(body: RegisterRequest) -> APIResponse:
    """注册新用户（普通用户角色）。"""
    username = body.username.strip()
    if not (_USERNAME_MIN <= len(username) <= _USERNAME_MAX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名长度需在 {_USERNAME_MIN}-{_USERNAME_MAX} 个字符之间",
        )
    if len(body.password) < _PASSWORD_MIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码长度至少 {_PASSWORD_MIN} 位",
        )
    if get_user_by_username(username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户名已存在: {username}",
        )

    user = create_user(
        username=username,
        password=body.password,
        nickname=body.nickname or username,
        role="user",
    )
    log.info("新用户注册: id=%s username=%s", user.id, user.username)
    return APIResponse(code=0, message="ok", data={"user": user.to_public()})


@router.post(
    "/login",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="校验用户名密码，签发 JWT（默认 24 小时有效）。",
)
async def login(body: LoginRequest) -> APIResponse:
    """登录并签发 JWT。失败统一返回 401（不区分用户名/密码错误）。"""
    user = authenticate(body.username.strip(), body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    settings = get_settings()
    token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        expires_seconds=settings.jwt_expire_seconds,
    )
    resp = LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_seconds,
        user=UserInfo(**user.to_public()),
    )
    log.info("用户登录: id=%s username=%s", user.id, user.username)
    return APIResponse(code=0, message="ok", data=resp.model_dump())


@router.get(
    "/me",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="当前用户信息",
    description="返回当前登录用户的信息（需携带 Bearer token）。",
)
async def me(user: User = Depends(get_current_user)) -> APIResponse:
    """返回当前登录用户信息。"""
    return APIResponse(code=0, message="ok", data=UserInfo(**user.to_public()).model_dump())
