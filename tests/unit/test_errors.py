"""
اختبارات الاستثناءات المخصصة
Unit Tests for Custom Exceptions
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.app.models.errors import (
    NexusError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ConflictError,
    DatabaseError,
    ServiceError,
    RateLimitError,
)


class TestNexusError:
    """اختبارات الاستثناء الأساسي"""
    
    def test_base_exception_creation(self):
        error = NexusError("Test message")
        assert error.message == "Test message"
        assert error.status_code == 500
        assert error.code is None
    
    def test_base_exception_with_code(self):
        error = NexusError("Test", code="TEST_CODE", status_code=400)
        assert error.message == "Test"
        assert error.code == "TEST_CODE"
        assert error.status_code == 400
    
    def test_to_dict(self):
        error = NexusError("Test message", code="TEST", status_code=400)
        result = error.to_dict()
        assert result["error"] == "NexusError"
        assert result["message"] == "Test message"
        assert result["status_code"] == 400
        assert result["code"] == "TEST"
    
    def test_inheritance(self):
        error = NexusError("Test")
        assert isinstance(error, Exception)


class TestValidationError:
    """اختبارات خطأ التحقق"""
    
    def test_creation(self):
        error = ValidationError("Invalid email", field="email")
        assert error.message == "Invalid email"
        assert error.status_code == 400
        assert error.code == "VALIDATION_ERROR"
        assert error.field == "email"
    
    def test_creation_without_field(self):
        error = ValidationError("Invalid data")
        assert error.field is None
    
    def test_to_dict(self):
        error = ValidationError("Invalid email", field="email")
        result = error.to_dict()
        assert result["error"] == "ValidationError"
        assert result["field"] == "email"


class TestAuthenticationError:
    """اختبارات خطأ المصادقة"""
    
    def test_creation_default(self):
        error = AuthenticationError()
        assert error.message == "Authentication failed"
        assert error.status_code == 401
        assert error.code == "AUTHENTICATION_ERROR"
    
    def test_creation_custom(self):
        error = AuthenticationError("Invalid password")
        assert error.message == "Invalid password"
        assert error.status_code == 401


class TestAuthorizationError:
    """اختبارات خطأ الصلاحيات"""
    
    def test_creation(self):
        error = AuthorizationError()
        assert error.message == "Insufficient permissions"
        assert error.status_code == 403
        assert error.code == "AUTHORIZATION_ERROR"


class TestResourceNotFoundError:
    """اختبارات خطأ المورد غير موجود"""
    
    def test_creation_with_identifier(self):
        error = ResourceNotFoundError("User", identifier="123")
        assert error.message == "User with id '123' not found"
        assert error.status_code == 404
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.resource == "User"
        assert error.identifier == "123"
    
    def test_creation_without_identifier(self):
        error = ResourceNotFoundError("Deal")
        assert error.message == "Deal not found"
        assert error.resource == "Deal"
        assert error.identifier is None
    
    def test_to_dict(self):
        error = ResourceNotFoundError("User", identifier="456")
        result = error.to_dict()
        assert result["resource"] == "User"
        assert result["identifier"] == "456"


class TestConflictError:
    """اختبارات خطأ التعارض"""
    
    def test_creation(self):
        error = ConflictError("Email already exists", field="email")
        assert error.message == "Email already exists"
        assert error.status_code == 409
        assert error.code == "CONFLICT_ERROR"
        assert error.field == "email"
    
    def test_to_dict(self):
        error = ConflictError("Username taken", field="username")
        result = error.to_dict()
        assert result["field"] == "username"


class TestDatabaseError:
    """اختبارات خطأ قاعدة البيانات"""
    
    def test_creation(self):
        error = DatabaseError()
        assert error.message == "Database error occurred"
        assert error.status_code == 500
        assert error.code == "DATABASE_ERROR"


class TestServiceError:
    """اختبارات خطأ الخدمة الخارجية"""
    
    def test_creation(self):
        error = ServiceError("TronGrid unavailable", service="TronGrid")
        assert error.message == "TronGrid unavailable"
        assert error.status_code == 503
        assert error.code == "SERVICE_ERROR"
        assert error.service == "TronGrid"
    
    def test_to_dict(self):
        error = ServiceError("Redis connection failed", service="Redis")
        result = error.to_dict()
        assert result["service"] == "Redis"


class TestRateLimitError:
    """اختبارات خطأ تجاوز الحد"""
    
    def test_creation(self):
        error = RateLimitError("Too many requests", retry_after=30)
        assert error.message == "Too many requests"
        assert error.status_code == 429
        assert error.code == "RATE_LIMIT_ERROR"
        assert error.retry_after == 30
    
    def test_creation_default(self):
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.retry_after == 60
    
    def test_to_dict(self):
        error = RateLimitError(retry_after=120)
        result = error.to_dict()
        assert result["retry_after"] == 120


__all__ = [
    "TestNexusError",
    "TestValidationError",
    "TestAuthenticationError",
    "TestAuthorizationError",
    "TestResourceNotFoundError",
    "TestConflictError",
    "TestDatabaseError",
    "TestServiceError",
    "TestRateLimitError",
]
