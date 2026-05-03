"""Image optimisation service – adapted for FastAPI's UploadFile.

Mirrors backend/services/image_service.py but uses:
  • FastAPI's UploadFile (instead of Flask's FileStorage)
  • Async read via ``await file.read()``
  • Returns the WebP filename for storage in DB
  • Writes to ``static/uploads/`` by default
"""

import io
import os
from typing import Optional

from fastapi import UploadFile

try:
    from PIL import Image
except ImportError:
    Image = None


async def save_and_optimize_image(
    file: UploadFile,
    filename: str,
    upload_folder: str = "static/uploads",
    max_size: tuple = (1280, 1280),
    quality: int = 75,
) -> Optional[str]:
    """Save an uploaded image, convert to WebP, return the relative filename.

    Parameters
    ----------
    file : UploadFile
        The file uploaded via FastAPI's ``File(...)`` / ``UploadFile``.
    filename : str
        Base name without extension (a UUID is recommended).
    upload_folder : str
        Relative or absolute path to the upload directory.
    max_size : tuple
        Maximum (width, height) for thumbnail resize.
    quality : int
        WebP quality (1-100).

    Returns
    -------
    str or None
        The output filename (e.g. ``"abc123.webp"``), or None on failure.
    """
    folder = upload_folder
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass

    base = os.path.splitext(filename)[0]
    out_name = f"{base}.webp"
    dest = os.path.join(folder, out_name)

    # Read all bytes from the uploaded file
    try:
        contents = await file.read()
    except Exception:
        return None

    if not contents:
        return None

    if Image is None:
        # Pillow not available - save raw bytes directly
        try:
            with open(dest, "wb") as f:
                f.write(contents)
            return out_name
        except Exception:
            return None

    try:
        # Open from memory (Pillow accepts bytes)
        img = Image.open(io.BytesIO(contents))

        # Convert palette to RGBA if needed
        if img.mode == "P":
            img = img.convert("RGBA")

        # Resize maintaining aspect ratio
        img.thumbnail(max_size, Image.LANCZOS)

        # Ensure RGB mode for WebP save
        if img.mode not in ("RGB", "RGBA"):
            try:
                img = img.convert("RGB")
            except Exception:
                pass

        save_kwargs = {"quality": quality, "method": 6}
        img.save(dest, "WEBP", **save_kwargs)
        return out_name
    except Exception:
        # Optimisation failed - fallback: save raw bytes
        try:
            with open(dest, "wb") as f:
                f.write(contents)
            return out_name
        except Exception:
            return None
