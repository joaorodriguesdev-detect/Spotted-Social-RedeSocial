import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
_profile = (os.getenv('SPOTTED_ENV', 'dev') or 'dev').strip().lower()
_profile_file = BASE_DIR / f'.env.{_profile}'
if _profile_file.exists():
    load_dotenv(_profile_file, override=True)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///spotted.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_SEED_ENABLED = os.getenv('ADMIN_SEED_ENABLED', 'false').lower() in ('1', 'true', 'yes')
    ADMIN_USERNAME = (os.getenv('ADMIN_USERNAME', 'admin') or 'admin').strip().lower()
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '').strip()

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    PUBLIC_FOLDER = os.getenv('PUBLIC_FOLDER', 'static/public')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(30 * 1024 * 1024)))

    DIRECT_ENABLED = os.getenv('DIRECT_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    SESSION_EXPIRE_DAYS = int(os.getenv('SESSION_EXPIRE_DAYS', '7'))
    PERMANENT_SESSION_LIFETIME = timedelta(days=SESSION_EXPIRE_DAYS)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() in ('1', 'true', 'yes')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() in ('1', 'true', 'yes')
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

    FEED_PAGE_SIZE = int(os.getenv('FEED_PAGE_SIZE', '8'))

    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    SOCKETIO_ALLOW_UPGRADES = os.getenv('SOCKETIO_ALLOW_UPGRADES', 'true').lower() in ('1', 'true', 'yes')
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')

    SPOTTED_ERROR_LOG = os.getenv('SPOTTED_ERROR_LOG', 'instance/error.log')

