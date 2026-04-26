"""
SafeSend Production Configuration
إعدادات الإنتاج - SafeSend
"""
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'safesend-prod-secret-2024')
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/safesend')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
    HEALTH_CHECK_TOKEN = os.getenv('HEALTH_CHECK_TOKEN', 'safesend-health-token-2024')
    CORS_ALLOWED_ORIGINS = ['*']
    RATE_LIMIT_PER_MINUTE = 60
    TRONGRID_API_URL = 'https://api.trongrid.io'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    JWT_ACCESS_TOKEN_EXPIRES = 900  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days
