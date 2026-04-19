import os

try:
    from PIL import Image
except Exception:
    Image = None


def save_and_optimize_image(file_storage, filename, upload_folder='static/uploads', max_size=(1280, 1280), quality=75):
    folder = upload_folder
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass

    base = os.path.splitext(filename)[0]
    out_name = f"{base}.webp"
    dest = os.path.join(folder, out_name)

    if Image is None:
        try:
            fallback_dest = os.path.join(folder, filename)
            file_storage.save(fallback_dest)
            return filename
        except Exception:
            return filename

    try:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass

        with Image.open(file_storage.stream) as img:
            if img.mode == 'P':
                img = img.convert('RGBA')

            img.thumbnail(max_size, Image.LANCZOS)

            save_kwargs = {'quality': quality, 'method': 6}
            if img.mode not in ('RGB', 'RGBA'):
                try:
                    img = img.convert('RGB')
                except Exception:
                    pass

            img.save(dest, 'WEBP', **save_kwargs)
            return out_name
    except Exception:
        try:
            try:
                file_storage.stream.seek(0)
            except Exception:
                pass
            fallback_dest = os.path.join(folder, filename)
            file_storage.save(fallback_dest)
            return filename
        except Exception:
            return filename

