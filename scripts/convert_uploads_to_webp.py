"""One-off script to convert existing uploads to WebP.

Run from the repository root (where `app.py` lives). This script will
process files under `static/uploads` and create corresponding `.webp`
files. It does not remove originals by default; set `REMOVE_ORIGINAL=True`
inside the script to delete the source files after successful conversion.

Usage:
    python scripts/convert_uploads_to_webp.py
"""
import os
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
ALLOWED = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
REMOVE_ORIGINAL = False


def convert_file(path):
    base, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext not in ALLOWED or ext == '.webp':
        return False
    out_path = base + '.webp'
    try:
        with Image.open(path) as img:
            if img.mode == 'P':
                img = img.convert('RGBA')
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            img.thumbnail((1280, 1280), Image.LANCZOS)
            img.save(out_path, 'WEBP', quality=80, method=6)
        if REMOVE_ORIGINAL:
            try:
                os.remove(path)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"Failed to convert {path}: {e}")
        return False


def main():
    if not os.path.isdir(BASE):
        print('Uploads folder not found:', BASE)
        return
    total = 0
    converted = 0
    for fname in os.listdir(BASE):
        full = os.path.join(BASE, fname)
        if not os.path.isfile(full):
            continue
        total += 1
        if convert_file(full):
            converted += 1
            print('Converted:', fname)
    print(f"Done. Processed {total} files, converted {converted}.")


if __name__ == '__main__':
    main()

