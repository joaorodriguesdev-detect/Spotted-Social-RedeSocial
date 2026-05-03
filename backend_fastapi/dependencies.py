"""Authentication dependencies using JWT stored in httpOnly cookies.

Provides:
- create_access_token() – generates a JWT
- get_current_user() – FastAPI dependency that reads the token from the
  httpOnly cookie, validates it, and returns the User model instance.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User


# ── Custom exception for banned users ──────────────────────────────────
class BannedUserException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta foi suspensa. Entre em contato com o suporte.",
        )


# ── Token creation ──────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT with an expiration claim."""
    to_encode = data.copy()
    # JWT spec requires 'sub' to be a string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or settings.ACCESS_TOKEN_EXPIRE_DELTA
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )


# ── FastAPI dependency ─────────────────────────────────────────────────
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract the current authenticated user.

    Tenta obter o token JWT de:
      1) Header Authorization: Bearer <token>
      2) Cookie httpOnly (access_token)
    """
    token = None
    # 1) Tenta do header Authorization
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    # 2) Fallback: cookie httpOnly
    if not token:
        token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
        )

    payload = decode_access_token(token)
    raw_sub = payload.get("sub")
    if raw_sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )
    user_id = int(raw_sub)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
        )

    # ── Verify user is not banned ──────────────────────────────────────
    if getattr(user, 'is_banned', False):
        raise BannedUserException()

    return user


# ── Optional auth (returns None if no cookie) ──────────────────────────
async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        raw_sub = payload.get("sub")
        if raw_sub is None:
            return None
        user_id = int(raw_sub)
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


# ── Admin-only dependency ──────────────────────────────────────────────
async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require that the authenticated user is an admin.

    Usage:
        @router.get("/admin/stats")
        async def stats(admin: User = Depends(get_current_admin)):
            ...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return current_user
