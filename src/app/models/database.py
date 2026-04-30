"""
إدارة قاعدة البيانات والجلسات
Database and Session Management
"""

import os
from typing import Generator, Optional
from urllib.parse import urlparse

from sqlalchemy import Engine, create_engine, text, event
from sqlalchemy.orm import Session, sessionmaker

from src.app.models.base import Base
from src.app.models.config import get_config, is_production, is_testing


def create_db_engine(database_url: Optional[str] = None) -> Engine:
    """إنشاء محرك قاعدة البيانات"""
    config = get_config()
    
    if database_url is None:
        database_url = config.SQLALCHEMY_DATABASE_URI
    
    engine_options = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 0,
        "pool_size": 5,
        "max_overflow": 0,
        "echo": False,
    }
    
    if is_production() or is_testing():
        if "postgresql" in database_url:
            engine_options.update({
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_recycle": 3600,
            })
    
    return create_engine(database_url, **engine_options)


engine = create_db_engine()

# Enable WAL mode for SQLite (supports concurrent reads/writes)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if 'sqlite' in str(type(dbapi_connection)):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """الحصول على جلسة جديدة"""
    return SessionLocal()


def init_db(app=None) -> None:
    """تهيئة قاعدة البيانات"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
    """حذف جميع الجداول"""
    if is_production():
        raise RuntimeError("Cannot drop tables in production environment")
    Base.metadata.drop_all(bind=engine)


def reset_database() -> None:
    """إعادة تعيين قاعدة البيانات"""
    drop_all_tables()
    init_db()


def check_connection() -> bool:
    """فحص اتصال قاعدة البيانات"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except Exception:
        return False


def get_database_info() -> dict:
    """الحصول على معلومات قاعدة البيانات"""
    config = get_config()
    db_url = config.SQLALCHEMY_DATABASE_URI
    
    if "@" in db_url:
        parts = db_url.split("@")
        if "://" in parts[0]:
            scheme, rest = parts[0].split("://", 1)
            if ":" in rest:
                user, _ = rest.split(":", 1)
                parts[0] = f"{scheme}://{user}:***"
        db_url = "@".join(parts)
    
    return {
        "url": db_url,
        "connected": check_connection(),
        "dialect": engine.dialect.name,
    }


def cleanup_connections() -> None:
    """تنظيف اتصالات قاعدة البيانات"""
    engine.dispose()


class SessionContext:
    """مدير سياق للجلسة"""
    
    def __init__(self):
        self.db: Optional[Session] = None
    
    def __enter__(self) -> Session:
        self.db = SessionLocal()
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.db.rollback()
        self.db.close()
        return False


def clean_schema_for_tests() -> None:
    """تنظيف المخطط للاختبارات"""
    if not is_testing():
        raise RuntimeError("This function is for testing only")
    
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()


__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "get_session",
    "init_db",
    "drop_all_tables",
    "reset_database",
    "check_connection",
    "get_database_info",
    "cleanup_connections",
    "SessionContext",
    "clean_schema_for_tests",
]
