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
import sys

# Import app and models to update DB image links. Importing `app` will run
# the app's import-time initialization (create tables, etc.). This script
# runs from the repository root (where app.py lives) so Python's import
# should find it. If you want to run this script without touching the
# application, run with `--no-db` to skip DB updates.
try:
    # Ensure repo root is on sys.path when running from scripts/
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from app import app, db, User, Post, Event, Conversation, DirectChatMessage
except Exception:
    app = None
    db = None
    User = Post = Event = Conversation = DirectChatMessage = None

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


def _print_progress(i, total, prefix='Progress'):
    # Simple ASCII progress bar
    try:
        bar_len = 40
        filled = int(round(bar_len * i / float(total))) if total else bar_len
        bar = '=' * filled + '-' * (bar_len - filled)
        print(f"\r{prefix} [{bar}] {i}/{total}", end='', flush=True)
    except Exception:
        print(f"\r{prefix} {i}/{total}", end='', flush=True)


def update_db_image_links():
    """Scan known model fields for image filenames that are NOT .webp and
    update them to point to the converted .webp filename when the file
    exists under `static/uploads` (and a .webp counterpart is present or
    can be created).

    The function updates these columns (if present):
      - User.profile_pic
      - Post.media_url
      - Event.media_url
      - Conversation.group_photo
      - DirectChatMessage.media_url
    """
    if not app or not db:
        print('\nDB support not available: could not import app. Skipping DB updates.')
        return

    with app.app_context():
        candidates = []
        mappings = [
            (User, 'profile_pic'),
            (Post, 'media_url'),
            (Event, 'media_url'),
            (Conversation, 'group_photo'),
            (DirectChatMessage, 'media_url')
        ]

        for Model, field in mappings:
            if Model is None:
                continue
            try:
                rows = Model.query.filter(getattr(Model, field).isnot(None)).all()
            except Exception:
                # Table might not exist in a fresh environment; skip safely
                continue
            for row in rows:
                try:
                    val = getattr(row, field)
                except Exception:
                    val = None
                if not val:
                    continue
                val = (val or '').strip()
                if not val:
                    continue
                # Skip external URLs or data URIs
                if val.startswith('http://') or val.startswith('https://') or val.startswith('data:'):
                    continue
                if val.lower().endswith('.webp'):
                    continue
                candidates.append((Model, row, field, val))

        total = len(candidates)
        if total == 0:
            print('\nNo DB image links to update.')
            return

        print(f'Found {total} DB image links to check. Scanning and updating when possible...')
        changed = 0
        processed = 0
        for idx, (Model, row, field, val) in enumerate(candidates, start=1):
            processed += 1
            _print_progress(processed, total, prefix='DB')
            # Determine basename and candidate paths
            basename = os.path.basename(val)
            # If value contains folder like 'static/uploads/xxx', strip to basename
            if os.path.isabs(val):
                src_path = val
            else:
                if val.startswith('static' + os.sep) or val.startswith('static/'):
                    # value includes static/ prefix
                    rel = val.split('static' + os.sep, 1)[-1] if 'static' + os.sep in val else val.split('static/', 1)[-1]
                    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', rel)
                else:
                    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', basename)

            new_base = os.path.splitext(os.path.basename(basename))[0] + '.webp'
            new_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', new_base)

            try:
                updated = False
                # If the .webp already exists, update DB to point to it
                if os.path.exists(new_path):
                    setattr(row, field, new_base)
                    updated = True
                else:
                    # If original file exists, attempt conversion
                    if os.path.exists(src_path):
                        if convert_file(src_path):
                            setattr(row, field, new_base)
                            updated = True
                if updated:
                    changed += 1
            except Exception:
                # don't abort on single-row failure
                pass

        # Commit if any changes
        print()  # newline after progress
        if changed:
            try:
                db.session.commit()
                print(f'Updated {changed} database record(s) to .webp filenames.')
            except Exception as e:
                print('Failed to commit DB changes:', e)
                try:
                    db.session.rollback()
                except Exception:
                    pass
        else:
            print('No database records were updated.')


if __name__ == '__main__':
    # Allow skipping DB integration if caller prefers
    skip_db = '--no-db' in sys.argv
    main()
    if not skip_db:
        update_db_image_links()


