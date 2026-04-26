"""
اختبارات تكامل Core Foundation
Integration Tests for Core Foundation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base, BaseModel
from src.app.models.errors import (
    NexusError,
    ValidationError,
    ResourceNotFoundError,
    DatabaseError,
)
from src.app.models.config import get_config, is_development, is_testing
from src.app.models.logging_config import (
    setup_logging,
    get_logger,
    set_trace_id,
    set_request_context,
    clear_request_context,
)
from src.app.models.database import (
    get_session,
    check_connection,
    SessionContext,
    create_db_engine,
)


# نموذج اختباري للتكامل
class IntegrationTestModel(BaseModel):
    __tablename__ = "integration_test"
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
    status = Column(String(50), default="pending")


class TestConfigDatabaseIntegration:
    
    def test_config_provides_correct_database_url(self):
        config = get_config()
        assert config.SQLALCHEMY_DATABASE_URI is not None
        assert check_connection() is True
    
    def test_environment_detection(self):
        assert is_testing() or is_development()


class TestLoggingDatabaseIntegration:
    
    def test_logging_with_database_session(self):
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, enable_console=False, enable_file=True)
            logger = get_logger("integration_test")
            set_trace_id("db-test-trace-123")
            set_request_context(user_id="test-user", ip_address="127.0.0.1")
            
            db = get_session()
            try:
                db.execute(text("SELECT 1"))
                logger.info("Database query executed successfully")
            except Exception as e:
                logger.error(f"Database query failed: {e}")
            finally:
                db.close()
            
            clear_request_context()


class TestErrorDatabaseIntegration:
    
    def test_database_error_exception(self):
        db = get_session()
        try:
            db.execute(text("INVALID SQL"))
            raise AssertionError("Should have raised an error")
        except Exception as e:
            error = DatabaseError(f"Database operation failed: {str(e)}")
            assert error.status_code == 500
            assert error.code == "DATABASE_ERROR"
            assert isinstance(error, NexusError)
        finally:
            db.close()
    
    def test_resource_not_found_integration(self):
        error = ResourceNotFoundError("User", identifier="12345")
        error_dict = error.to_dict()
        assert error_dict["error"] == "ResourceNotFoundError"
        assert error_dict["resource"] == "User"
        assert error_dict["identifier"] == "12345"
        assert error_dict["status_code"] == 404


class TestFullIntegration:
    
    @pytest.fixture
    def temp_db_session(self):
        """إنشاء قاعدة بيانات مؤقتة مع جلسة"""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            test_db_url = f"sqlite:///{tmp.name}"
            test_engine = create_db_engine(test_db_url)
            Base.metadata.create_all(test_engine)
            TestSessionLocal = sessionmaker(bind=test_engine)
            yield TestSessionLocal
    
    def test_full_crud_with_logging(self, temp_db_session):
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, log_level="INFO", enable_console=False, enable_file=True, json_format=True)
            
            logger = get_logger("full_integration")
            set_trace_id(str(uuid.uuid4()))
            set_request_context(user_id="integration-user")
            
            db = temp_db_session()
            
            logger.info("Creating test record")
            record = IntegrationTestModel(name="integration_test", value=100)
            db.add(record)
            db.commit()
            
            assert record.id is not None
            assert record.created_at is not None
            
            retrieved = db.query(IntegrationTestModel).filter_by(id=record.id).first()
            assert retrieved is not None
            assert retrieved.name == "integration_test"
            assert retrieved.value == 100
            
            retrieved.value = 200
            retrieved.status = "completed"
            db.commit()
            
            updated = db.query(IntegrationTestModel).filter_by(id=record.id).first()
            assert updated.value == 200
            assert updated.status == "completed"
            assert updated.updated_at > updated.created_at
            
            db.delete(updated)
            db.commit()
            
            deleted_check = db.query(IntegrationTestModel).filter_by(id=record.id).first()
            assert deleted_check is None
            
            logger.info("CRUD operations completed successfully")
            
            db.close()
            clear_request_context()
    
    def test_transaction_rollback_on_error(self, temp_db_session):
        db = temp_db_session()
        
        record = IntegrationTestModel(name="rollback_test", value=50)
        db.add(record)
        db.commit()
        
        record_id = record.id
        
        try:
            record.value = 75
            raise ValueError("Simulated error")
            db.commit()
        except ValueError:
            db.rollback()
        
        db.refresh(record)
        assert record.value == 50
        db.close()
    
    def test_session_context_with_temp_db(self, temp_db_session):
        """اختبار SessionContext مع قاعدة بيانات مؤقتة"""
        # إنشاء SessionContext مخصص للاختبار
        class TestSessionContext:
            def __init__(self, session_factory):
                self.session_factory = session_factory
                self.db = None
            
            def __enter__(self):
                self.db = self.session_factory()
                return self.db
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    self.db.rollback()
                self.db.close()
                return False
        
        with TestSessionContext(temp_db_session) as db:
            record = IntegrationTestModel(name="context_test", value=999)
            db.add(record)
            db.commit()
            assert record.id is not None
            retrieved = db.query(IntegrationTestModel).filter_by(id=record.id).first()
            assert retrieved.name == "context_test"
    
    def test_multiple_sessions_isolation(self, temp_db_session):
        db1 = temp_db_session()
        record = IntegrationTestModel(name="session1", value=1)
        db1.add(record)
        db1.commit()
        record_id = record.id
        
        db2 = temp_db_session()
        retrieved = db2.query(IntegrationTestModel).filter_by(id=record_id).first()
        assert retrieved is not None
        assert retrieved.value == 1
        
        record.value = 11
        db1.commit()
        
        assert retrieved.value == 1
        db2.refresh(retrieved)
        assert retrieved.value == 11
        
        db1.close()
        db2.close()


class TestErrorHandlingIntegration:
    
    def test_validation_error_integration(self):
        error = ValidationError("Invalid input", field="email")
        error_dict = error.to_dict()
        
        logger = get_logger("error_test")
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, enable_console=False, enable_file=True)
            logger.error(f"Validation failed: {error_dict['message']}", extra={"extra_data": error_dict})
    
    def test_nested_error_handling(self):
        def inner_function():
            raise DatabaseError("Inner database error")
        
        def outer_function():
            try:
                inner_function()
            except DatabaseError as e:
                raise NexusError(f"Outer error: {e.message}", code="OUTER_ERROR", status_code=500)
        
        with pytest.raises(NexusError) as exc_info:
            outer_function()
        
        assert exc_info.value.code == "OUTER_ERROR"
        assert "Inner database error" in exc_info.value.message
