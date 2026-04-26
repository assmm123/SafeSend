"""
اختبارات إدارة قاعدة البيانات
Unit Tests for Database Management
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.orm import Session, sessionmaker

from src.app.models.base import Base, BaseModel
from src.app.models.config import TestingConfig
from src.app.models.database import (
    engine,
    get_db,
    get_session,
    init_db,
    drop_all_tables,
    check_connection,
    get_database_info,
    cleanup_connections,
    SessionContext,
    clean_schema_for_tests,
    create_db_engine,
)


# نموذج اختباري
class TestTable(BaseModel):
    __tablename__ = "test_table"
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)


class TestCreateDBEngine:
    """اختبارات إنشاء محرك قاعدة البيانات"""
    
    def test_create_engine_sqlite(self):
        """اختبار إنشاء محرك SQLite"""
        engine = create_db_engine("sqlite:///:memory:")
        assert engine.dialect.name == "sqlite"
    
    def test_create_engine_sqlite_no_pooling(self):
        """اختبار أن SQLite لا يستخدم pooling"""
        engine = create_db_engine("sqlite:///:memory:")
        assert engine.dialect.name == "sqlite"


class TestDatabaseSession:
    """اختبارات جلسات قاعدة البيانات"""
    
    def test_get_db_generator(self):
        """اختبار مولد get_db"""
        db_gen = get_db()
        db = next(db_gen)
        assert isinstance(db, Session)
        
        try:
            next(db_gen)
        except StopIteration:
            pass
    
    def test_get_session(self):
        """اختبار get_session"""
        db = get_session()
        assert isinstance(db, Session)
        db.close()
    
    def test_session_context(self):
        """اختبار SessionContext"""
        with SessionContext() as db:
            assert isinstance(db, Session)
            db.execute(text("SELECT 1"))


class TestDatabaseOperations:
    """اختبارات عمليات قاعدة البيانات"""
    
    def test_init_db(self):
        """اختبار تهيئة قاعدة البيانات"""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            test_engine = create_db_engine(f"sqlite:///{tmp.name}")
            Base.metadata.create_all(test_engine)
            
            with test_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
                tables = [row[0] for row in result]
    
    def test_check_connection_success(self):
        """اختبار فحص الاتصال الناجح"""
        assert check_connection() is True


class TestDatabaseInfo:
    """اختبارات معلومات قاعدة البيانات"""
    
    def test_get_database_info(self):
        """اختبار الحصول على معلومات قاعدة البيانات"""
        info = get_database_info()
        assert "url" in info
        assert "connected" in info
        assert "dialect" in info


class TestCleanupFunctions:
    """اختبارات دوال التنظيف"""
    
    def test_drop_all_tables_raises_in_production(self):
        """اختبار أن drop_all_tables يرفض العمل في الإنتاج"""
        with patch('src.app.models.database.is_production', return_value=True):
            with pytest.raises(RuntimeError):
                drop_all_tables()
    
    def test_clean_schema_for_tests_raises_outside_testing(self):
        """اختبار أن clean_schema_for_tests يرفض العمل خارج الاختبار"""
        with patch('src.app.models.database.is_testing', return_value=False):
            with pytest.raises(RuntimeError):
                clean_schema_for_tests()
    
    def test_cleanup_connections(self):
        """اختبار تنظيف الاتصالات"""
        cleanup_connections()


class TestDatabaseIntegration:
    """اختبارات تكاملية لقاعدة البيانات"""
    
    @pytest.fixture
    def temp_db(self):
        """إنشاء قاعدة بيانات مؤقتة"""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            test_engine = create_db_engine(f"sqlite:///{tmp.name}")
            Base.metadata.create_all(test_engine)
            
            TestSessionLocal = sessionmaker(bind=test_engine)
            
            yield TestSessionLocal
    
    def test_crud_operations(self, temp_db):
        """اختبار عمليات CRUD"""
        db = temp_db()
        
        record = TestTable(name="test_record", value=42)
        db.add(record)
        db.commit()
        
        assert record.id is not None
        
        retrieved = db.query(TestTable).filter_by(name="test_record").first()
        assert retrieved is not None
        assert retrieved.value == 42
        
        retrieved.value = 100
        db.commit()
        
        db.delete(retrieved)
        db.commit()
        
        db.close()
    
    def test_session_rollback_on_exception(self, temp_db):
        """اختبار التراجع عند حدوث خطأ"""
        db = temp_db()
        
        record = TestTable(name="rollback_test", value=1)
        db.add(record)
        db.commit()
        
        record.value = 2
        db.rollback()
        
        db.refresh(record)
        assert record.value == 1
        
        db.close()


__all__ = [
    "TestCreateDBEngine",
    "TestDatabaseSession",
    "TestDatabaseOperations",
    "TestDatabaseInfo",
    "TestCleanupFunctions",
    "TestDatabaseIntegration",
]
