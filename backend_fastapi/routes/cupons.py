"""Coupon (Cupom) routes – CRUD + redeem.

This is an EXAMPLE of how a new feature module looks in FastAPI,
migrating the patterns found in the original Flask routes:

  • APIRouter instead of Blueprint
  • async def everywhere
  • Pydantic schemas for input/output validation
  • Return dicts / Pydantic models instead of jsonify()
  • SQLAlchemy async queries
  • Auth via JWT httpOnly cookie dependency
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db # No change here
from dependencies import get_current_user # No change here
from models import Coupon, User # Import from models/__init__.py
from utils import br_time # Centralized import

from schemas.cupons import (
    CouponBrief,
    CouponCreate,
    CouponResponse,
    CouponUpdate,
    CouponUseRequest,
)

router = APIRouter(prefix="/cupons", tags=["cupons"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CRUD – Admin / Authenticated                                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── GET /cupons ────────────────────────────────────────────────────────
@router.get("/", response_model=List[CouponBrief])
async def list_coupons(
    active_only: bool = Query(False, description="Filtrar apenas cupons ativos"),
    search: Optional[str] = Query(None, max_length=50, description="Buscar por código ou título"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # requires auth
):
    """List all coupons (authenticated users)."""
    query = select(Coupon).order_by(Coupon.created_at.desc())

    if active_only:
        query = query.where(Coupon.is_active.is_(True))

    if search:
        pattern = f"%{search.upper()}%"
        query = query.where(
            (Coupon.code.ilike(pattern)) | (Coupon.title.ilike(pattern))
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    coupons = result.scalars().all()
    return [CouponBrief.model_validate(c) for c in coupons]


# ── GET /cupons/{coupon_id} ────────────────────────────────────────────
@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single coupon by ID."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")
    return CouponResponse.model_validate(coupon)


# ── GET /cupons/code/{code} ────────────────────────────────────────────
@router.get("/code/{code}", response_model=CouponResponse)
async def get_coupon_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up a coupon by its unique code."""
    result = await db.execute(select(Coupon).where(Coupon.code == code.upper().strip()))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")
    return CouponResponse.model_validate(coupon)


# ── POST /cupons ───────────────────────────────────────────────────────
@router.post("/", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new coupon (authenticated users).

    This is the "Criação de Cupons" endpoint you asked for.
    It follows the same pattern as the old Flask routes but with:
      - async def
      - Pydantic validation
      - Direct return (no jsonify)
    """
    # Check unique code
    result = await db.execute(select(Coupon).where(Coupon.code == payload.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um cupom com o código '{payload.code}'.",
        )

    coupon = Coupon(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        discount_percent=payload.discount_percent,
        max_uses=payload.max_uses,
        expires_at=payload.expires_at,
        user_id=current_user.id,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    return CouponResponse.model_validate(coupon)


# ── PATCH /cupons/{coupon_id} ──────────────────────────────────────────
@router.patch("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing coupon (partial update)."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")

    # Only the creator or an admin can update
    if coupon.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para editar este cupom.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    await db.commit()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon)


# ── DELETE /cupons/{coupon_id} ─────────────────────────────────────────
@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a coupon (creator or admin only)."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")

    if coupon.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para excluir este cupom.",
        )

    await db.delete(coupon)
    await db.commit()
    # 204 No Content -> no response body


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  REDEEM / USE                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── POST /cupons/usar ──────────────────────────────────────────────────
@router.post("/usar", response_model=CouponResponse)
async def use_coupon(
    payload: CouponUseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redeem / use a coupon by its code.

    This increments the current_uses counter and validates:
      - Coupon exists and is active
      - Not expired
      - Hasn't reached max_uses (if limited)
    """
    result = await db.execute(select(Coupon).where(Coupon.code == payload.code))
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cupom não encontrado.",
        )

    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este cupom está inativo.",
        )

    # Check expiration
    if coupon.expires_at and coupon.expires_at < br_time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este cupom já expirou.",
        )

    # Check usage limit
    if coupon.max_uses > 0 and coupon.current_uses >= coupon.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este cupom já atingiu o limite de usos.",
        )

    coupon.current_uses += 1
    await db.commit()
    await db.refresh(coupon)

    return CouponResponse.model_validate(coupon)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STATS (example of aggregation)                                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/stats/summary")
async def coupon_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate stats about coupons (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores.")

    result = await db.execute(select(Coupon))
    all_coupons = result.scalars().all()

    total = len(all_coupons)
    active = sum(1 for c in all_coupons if c.is_active)
    total_uses = sum(c.current_uses for c in all_coupons)

    return {
        "total_coupons": total,
        "active_coupons": active,
        "inactive_coupons": total - active,
        "total_uses": total_uses,
    }
