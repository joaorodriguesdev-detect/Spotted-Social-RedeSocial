# modules/config.py - Configurações da aplicação

import os
from datetime import timedelta

def get_config():
    """Retorna todas as configurações da aplicação."""
    config = {
        'SECRET_KEY': os.environ.get('SECRET_KEY'),
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///spotted.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'UPLOAD_FOLDER': 'static/uploads',
        'PUBLIC_FOLDER': 'static/public',
        'MAX_CONTENT_LENGTH': 30 * 1024 * 1024,  # 30MB
        'DIRECT_ENABLED': True,
        'SESSION_EXPIRE_DAYS': int(os.environ.get('SESSION_EXPIRE_DAYS', '7')),
        'FEED_PAGE_SIZE': get_feed_page_size(),
        'SOCKETIO_CORS': os.environ.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
        'SOCKETIO_ALLOW_UPGRADES': os.environ.get('SOCKETIO_ALLOW_UPGRADES', 'True').lower() in ('1', 'true', 'yes'),
        'SOCKETIO_ASYNC_MODE': get_socketio_async_mode(),
    }
    return config


def get_feed_page_size():
    """Obtém o tamanho da página do feed com validação."""
    ALLOWED_SIZES = {6, 8, 12}
    raw_value = os.environ.get('FEED_PAGE_SIZE', '8')
    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        return 8
    return parsed_value if parsed_value in ALLOWED_SIZES else 8


def get_socketio_async_mode():
    """Obtém o modo assíncrono do SocketIO (gevent ou threading)."""
    socketio_env_mode = os.environ.get('SOCKETIO_ASYNC_MODE')
    if socketio_env_mode:
        return socketio_env_mode

    try:
        import gevent
        return 'gevent'
    except Exception:
        return 'threading'


def get_session_lifetime(days):
    """Retorna o tempo de vida da sessão."""
    return timedelta(days=days)


def get_error_log_path():
    """Obtém o caminho para o arquivo de log de erros."""
    return os.environ.get('SPOTTED_ERROR_LOG', 'instance/error.log')

