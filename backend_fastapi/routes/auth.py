"""
Auth routes - registro, login, logout, me.

All column names match models/user.py EXACTLY:
  - User.password_hash
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import create_access_token, get_current_user
from models.user import User
from utils import br_time
from schemas.auth import AuthResponse, LoginRequest, LogoutResponse, RegisterRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        existing = await db.execute(select(User).where(User.username == payload.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ja existe.")
        if len(payload.password) < 8 or not re.search(r"[#@$%*]", payload.password):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha invalida.")
        user = User(
            name=payload.name or "",
            username=payload.username,
            password_hash=bcrypt.hash(str(payload.password)),
            university=payload.university,
            created_at=br_time(),
        )
        db.add(user)
        await db.flush()
        token = create_access_token(data={"sub": user.id})
        response.set_cookie(
            key=settings.JWT_COOKIE_NAME, value=token, httponly=True,
            secure=settings.JWT_COOKIE_SECURE, samesite=settings.JWT_COOKIE_SAMESITE,
            max_age=int(settings.ACCESS_TOKEN_EXPIRE_DELTA.total_seconds()), path="/",
        )
        logger.info(f"Usuario registrado: {user.id}")
        return AuthResponse(
            user_id=user.id, username=user.username, name=user.name,
            profile_pic=user.profile_pic, is_admin=user.is_admin, token=token,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro no registro: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.")


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario ou senha incorretos.")
        if not bcrypt.verify(str(payload.password), user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario ou senha incorretos.")
        token = create_access_token(data={"sub": user.id})
        response.set_cookie(
            key=settings.JWT_COOKIE_NAME, value=token, httponly=True,
            secure=settings.JWT_COOKIE_SECURE, samesite=settings.JWT_COOKIE_SAMESITE,
            max_age=int(settings.ACCESS_TOKEN_EXPIRE_DELTA.total_seconds()), path="/",
        )
        logger.info(f"Login: {user.id}")
        return AuthResponse(
            user_id=user.id, username=user.username, name=user.name,
            profile_pic=user.profile_pic, is_admin=user.is_admin,
            token=token,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro no login: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.")


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    response.delete_cookie(
        key=settings.JWT_COOKIE_NAME, path="/",
        httponly=True, secure=settings.JWT_COOKIE_SECURE, samesite=settings.JWT_COOKIE_SAMESITE,
    )
    return LogoutResponse()


@router.get("/me", response_model=AuthResponse)
async def me(current_user: User = Depends(get_current_user)):
    try:
        return AuthResponse(
            user_id=current_user.id, username=current_user.username, name=current_user.name,
            profile_pic=current_user.profile_pic, is_admin=current_user.is_admin,
        )
    except Exception as e:
        logger.exception(f"Erro no /me: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.")
