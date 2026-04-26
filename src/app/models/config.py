"""
إعدادات التطبيق
Application Configuration

هذا الملف يحتوي على إعدادات التطبيق لمختلف البيئات.
جميع المفاتيح الحساسة تُقرأ من متغيرات البيئة (.env).
This file contains application settings for different environments.
All sensitive keys are read from environment variables (.env).
"""

import os
from typing import Optional


class Config:
    """
    الإعدادات الأساسية المشتركة بين جميع البيئات
    Base configuration shared across all environments
    
    Attributes:
        SECRET_KEY (str): مفتاح التشفير العام / General secret key
        JWT_SECRET_KEY (str): مفتاح توكن JWT / JWT secret key
        BCRYPT_ROUNDS (int): عدد جولات bcrypt / bcrypt rounds
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): تعطيل تتبع التعديلات
        BACKUP_DIR (str): مجلد النسخ الاحتياطي / Backup directory
        BACKUP_RETENTION_DAYS (int): أيام الاحتفاظ بالنسخ / Retention days
    """
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    }
    
    # Backup
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "./backups")
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/hour"
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_API: str = "60/minute"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


class DevelopmentConfig(Config):
    """
    إعدادات بيئة التطوير
    Development environment configuration
    
    يستخدم SQLite للتطوير المحلي.
    Uses SQLite for local development.
    """
    
    DEBUG: bool = True
    TESTING: bool = False
    
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///nexus_dev.db"
    )
    
    # Disable pooling for SQLite
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
    }
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    
    # Cache
    CACHE_TYPE: str = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT: int = 300


class TestingConfig(Config):
    """
    إعدادات بيئة الاختبار
    Testing environment configuration
    
    يجب استخدام PostgreSQL للاختبارات حسب القاعدة 9.
    Must use PostgreSQL for testing as per rule 9.
    """
    
    DEBUG: bool = False
    TESTING: bool = True
    
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://localhost:5432/nexus_test"
    )
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED: bool = False
    
    # Faster bcrypt for testing
    BCRYPT_ROUNDS: int = 4
    
    # Logging
    LOG_LEVEL: str = "WARNING"
    
    # Cache
    CACHE_TYPE: str = "NullCache"


class ProductionConfig(Config):
    """
    إعدادات بيئة الإنتاج
    Production environment configuration
    
    يجب استخدام PostgreSQL للإنتاج حسب القاعدة 9.
    Must use PostgreSQL for production as per rule 9.
    """
    
    DEBUG: bool = False
    TESTING: bool = False
    
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/nexus_prod"
    )
    
    # Stricter security
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    
    REMEMBER_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    
    # CSRF
    WTF_CSRF_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Cache
    CACHE_TYPE: str = "RedisCache"
    CACHE_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT: int = 3600
    
    # Monitoring
    METRICS_ENABLED: bool = True


# قاموس البيئات المتاحة
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env: Optional[str] = None) -> Config:
    """
    جلب الإعدادات المناسبة للبيئة الحالية
    Get appropriate configuration for current environment
    
    Args:
        env (Optional[str]): اسم البيئة (development, testing, production)
                            Environment name (development, testing, production)
    
    Returns:
        Config: كائن الإعدادات المناسب / Appropriate config object
    
    Raises:
        ValueError: إذا كانت البيئة غير معروفة / If environment is unknown
    
    Example:
        >>> config = get_config("development")
        >>> print(config.DEBUG)
        True
    """
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    
    if env not in config_by_name:
        raise ValueError(
            f"Unknown environment: '{env}'. "
            f"Valid options: {', '.join(config_by_name.keys())}"
        )
    
    return config_by_name[env]()


def get_database_url() -> str:
    """
    جلب عنوان اتصال قاعدة البيانات الحالي
    Get current database connection URL
    
    Returns:
        str: عنوان اتصال قاعدة البيانات / Database connection URL
    """
    config = get_config()
    return config.SQLALCHEMY_DATABASE_URI


def is_production() -> bool:
    """
    التحقق مما إذا كنا في بيئة الإنتاج
    Check if we are in production environment
    
    Returns:
        bool: True إذا كنا في الإنتاج / True if in production
    """
    env = os.getenv("FLASK_ENV", "development")
    return env == "production"


def is_testing() -> bool:
    """
    التحقق مما إذا كنا في بيئة الاختبار
    Check if we are in testing environment
    
    Returns:
        bool: True إذا كنا في الاختبار / True if in testing
    """
    env = os.getenv("FLASK_ENV", "development")
    return env == "testing" or bool(os.getenv("TESTING", False))


def is_development() -> bool:
    """
    التحقق مما إذا كنا في بيئة التطوير
    Check if we are in development environment
    
    Returns:
        bool: True إذا كنا في التطوير / True if in development
    """
    env = os.getenv("FLASK_ENV", "development")
    return env == "development"


__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "config_by_name",
    "get_config",
    "get_database_url",
    "is_production",
    "is_testing",
    "is_development",
]
