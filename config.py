import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'spotted_university_ultra_v8_final_fix')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///spotted.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    PUBLIC_FOLDER = os.getenv('PUBLIC_FOLDER', 'static/public')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(30 * 1024 * 1024)))

    DIRECT_ENABLED = os.getenv('DIRECT_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    SESSION_EXPIRE_DAYS = int(os.getenv('SESSION_EXPIRE_DAYS', '7'))
    PERMANENT_SESSION_LIFETIME = timedelta(days=SESSION_EXPIRE_DAYS)

    FEED_PAGE_SIZE = int(os.getenv('FEED_PAGE_SIZE', '8'))

    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    SOCKETIO_ALLOW_UPGRADES = os.getenv('SOCKETIO_ALLOW_UPGRADES', 'true').lower() in ('1', 'true', 'yes')
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')

    SPOTTED_ERROR_LOG = os.getenv('SPOTTED_ERROR_LOG', 'instance/error.log')

