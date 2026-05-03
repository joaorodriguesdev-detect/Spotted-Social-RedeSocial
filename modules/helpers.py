# modules/helpers.py - Funções auxiliares e utilitários

import os
import re
from datetime import datetime
from flask import session

try:
    from PIL import Image
except Exception:
    Image = None


def save_and_optimize_image(file_storage, filename, upload_folder=None, max_size=(1280, 1280), quality=75):
    """
    Salva uma imagem carregada e a converte para WebP.

    - Se filename não tiver extensão, adiciona .webp
    - Se Pillow não estiver disponível, salva na pasta diretamente
    - Retorna o nome do arquivo final (geralmente com .webp)
    """
    folder = upload_folder or 'static/uploads'
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass

    # Garante que temos um nome base sem extensão
    base = os.path.splitext(filename)[0]
    out_name = f"{base}.webp"
    dest = os.path.join(folder, out_name)

    if Image is None:
        # Pillow não instalado; tenta salvar diretamente
        try:
            fallback_dest = os.path.join(folder, filename)
            file_storage.save(fallback_dest)
            return filename
        except Exception:
            return filename

    try:
        # Reseta a stream para o início
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass

        with Image.open(file_storage.stream) as img:
            # Converte paleta para RGBA se necessário
            if img.mode == 'P':
                img = img.convert('RGBA')

            # Redimensiona mantendo aspect ratio
            img.thumbnail(max_size, Image.LANCZOS)

            save_kwargs = {'quality': quality, 'method': 6}
            # Converte para RGB se necessário
            if img.mode not in ('RGB', 'RGBA'):
                try:
                    img = img.convert('RGB')
                except Exception:
                    pass

            # Salva como WebP
            img.save(dest, 'WEBP', **save_kwargs)
            return out_name
    except Exception:
        # Se otimização falha, tenta salvar diretamente
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


def notify_mentions(db, content, sender_name, post_id):
    """
    Encontra menções (@username) em um conteúdo e notifica os usuários.
    """
    from modules.models import User, Notification

    mentions = re.findall(r'@(\w+)', content)
    for username in mentions:
        user = User.query.filter_by(username=username.lower()).first()
        if user and user.id != session.get('user_id'):
            db.session.add(Notification(
                user_id=user.id,
                sender_name=sender_name,
                action_type="mencionou você em uma publicação",
                post_id=post_id
            ))


def resolve_user_by_sender_name(db, sender_name):
    """
    Encontra um usuário pelo nome do remetente (username ou display name).
    """
    from sqlalchemy import func
    from modules.models import User

    if not sender_name:
        return None

    normalized_sender = sender_name.strip().lower()
    if not normalized_sender:
        return None

    # Prefere username exato, depois fallback para display name
    user = User.query.filter(func.lower(User.username) == normalized_sender).first()
    if user:
        return user

    # Tenta encontrar pelo display name
    user = User.query.filter(func.lower(User.name) == normalized_sender).first()
    return user


def build_event_post_content(title, location, event_date, description, username):
    """
    Constrói o conteúdo de uma postagem de evento para o feed.
    """
    return f"📢 NOVO EVENTO:\n\n{title}\n📍 {location}\n📅 {event_date}\n\nDescrição: {description}\n\nPost criado por @{username}"


def sync_event_feed_post(db, event, old_title, old_location, old_event_date, old_description):
    """
    Sincroniza as mudanças de um evento com sua postagem no feed.
    """
    from modules.models import Post

    # Procura pela postagem do evento usando o marcador
    old_content = build_event_post_content(old_title, old_location, old_event_date, old_description, event.creator.username if event.creator else 'admin')
    feed_post = Post.query.filter_by(user_id=event.user_id, content=old_content).first()

    if feed_post:
        new_content = build_event_post_content(event.title, event.location, event.event_date, event.description, event.creator.username if event.creator else 'admin')
        feed_post.content = new_content
        if event.media_url:
            feed_post.media_url = event.media_url
        db.session.commit()


def users_follow_each_other(user1, user2):
    """
    Verifica se dois usuários se seguem mutuamente.
    """
    return user1.is_following(user2) and user2.is_following(user1)


def is_direct_globally_disabled():
    """
    Verifica se o Direct (mensagens) está desabilitado globalmente.
    """
    from flask import current_app
    return not current_app.config.get('DIRECT_ENABLED', True)


def is_direct_blocked_for_system_admin():
    """Helper para compatibilidade - retorna False (não é mais bloqueado)."""
    return False


def is_direct_temporarily_disabled_for_users():
    """Helper para compatibilidade - retorna False (não é mais bloqueado)."""
    return False

