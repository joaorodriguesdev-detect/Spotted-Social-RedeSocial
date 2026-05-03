"""Upload routes – profile pictures and post media.

Provides:
  • POST /api/upload/profile-pic – update current user's profile picture
  • POST /api/upload/post-media – upload media for a new post

Uses FastAPI's UploadFile / File() and the async image_service.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db # No change here
from dependencies import get_current_user # No change here
from models import User # Import from models/__init__.py
from services.image_service import save_and_optimize_image

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
}


def _validate_file(file: UploadFile) -> None:
    """Check MIME type and file size."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de arquivo '{file.content_type}' não permitido. Use JPEG, PNG, WebP, GIF ou AVIF.",
        )
    # FastAPI already limits size via max_size in File(), but we check anyway
    # The content-length header may not always be present


# ── POST /api/upload/profile-pic ───────────────────────────────────────
@router.post("/profile-pic", response_model=dict)
async def upload_profile_pic(
    file: UploadFile = File(..., description="Imagem de perfil (JPEG, PNG, WebP)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new profile picture for the current user.

    The image is converted to WebP and stored in ``static/uploads/``.
    The user's ``profile_pic`` field is updated with the filename.
    """
    _validate_file(file)

    # Generate a unique filename
    filename_base = f"pfp_{current_user.id}_{uuid.uuid4().hex[:8]}"

    filename = await save_and_optimize_image(
        file,
        filename_base,
        upload_folder="static/uploads",
    )

    if not filename:
        raise HTTPException(
            status_code=500,
            detail="Falha ao processar a imagem.",
        )

    # Update user profile
    current_user.profile_pic = filename
    await db.commit()

    return {
        "ok": True,
        "filename": filename,
        "url": f"/static/uploads/{filename}",
    }


# ── POST /api/upload/post-media ────────────────────────────────────────
@router.post("/post-media", response_model=dict)
async def upload_post_media(
    file: UploadFile = File(..., description="Mídia para o post (imagem)"),
    current_user: User = Depends(get_current_user),
):
    """Upload a media file for a post.

    Returns the filename so the client can then create the post with it.
    """
    _validate_file(file)

    filename_base = f"post_{uuid.uuid4().hex[:12]}"

    filename = await save_and_optimize_image(
        file,
        filename_base,
        upload_folder="static/uploads",
    )

    if not filename:
        raise HTTPException(
            status_code=500,
            detail="Falha ao processar a imagem.",
        )

    return {
        "ok": True,
        "filename": filename,
        "url": f"/static/uploads/{filename}",
    }
