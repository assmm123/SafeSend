"""
استثناءات مخصصة لنظام Nexus
Custom Exceptions for Nexus System

هذا الملف يحتوي على جميع الاستثناءات المخصصة المستخدمة في النظام.
This file contains all custom exceptions used in the system.
"""

from typing import Optional


class NexusError(Exception):
    """
    الاستثناء الأساسي لجميع أخطاء النظام
    Base exception for all Nexus errors
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        code (str): كود الخطأ (اختياري) / Error code (optional)
        status_code (int): كود HTTP المناسب / Appropriate HTTP status code
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """
        تحويل الاستثناء إلى قاموس للاستجابة في API
        Convert exception to dictionary for API response
        
        Returns:
            dict: قاموس يحتوي على تفاصيل الخطأ
        """
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code
        }
        if self.code:
            result["code"] = self.code
        return result


class ValidationError(NexusError):
    """
    خطأ في التحقق من صحة البيانات المدخلة
    Validation error for input data
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        field (str): اسم الحقل المرتبط بالخطأ / Related field name
    """
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400
        )
        self.field = field
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.field:
            result["field"] = self.field
        return result


class AuthenticationError(NexusError):
    """
    خطأ في المصادقة - فشل تسجيل الدخول أو توكن غير صالح
    Authentication error - login failure or invalid token
    
    Attributes:
        message (str): رسالة الخطأ / Error message
    """
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(NexusError):
    """
    خطأ في الصلاحيات - المستخدم ليس لديه صلاحية كافية
    Authorization error - insufficient permissions
    
    Attributes:
        message (str): رسالة الخطأ / Error message
    """
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403
        )


class ResourceNotFoundError(NexusError):
    """
    المورد المطلوب غير موجود
    Requested resource not found
    
    Attributes:
        resource (str): نوع المورد / Resource type
        identifier (str): معرف المورد / Resource identifier
    """
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404
        )
        self.resource = resource
        self.identifier = identifier
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["resource"] = self.resource
        if self.identifier:
            result["identifier"] = self.identifier
        return result


class ConflictError(NexusError):
    """
    خطأ تعارض في البيانات - مثل إيميل أو اسم مستخدم مكرر
    Conflict error - duplicate email or username
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        field (str): الحقل المتعارض / Conflicting field
    """
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=409
        )
        self.field = field
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.field:
            result["field"] = self.field
        return result


class DatabaseError(NexusError):
    """
    خطأ في قاعدة البيانات
    Database error
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        original_error (Exception): الخطأ الأصلي / Original exception
    """
    
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500
        )


class ServiceError(NexusError):
    """
    خطأ في خدمة خارجية - مثل TronGrid أو Redis
    External service error - TronGrid or Redis
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        service (str): اسم الخدمة / Service name
    """
    
    def __init__(self, message: str, service: Optional[str] = None):
        super().__init__(
            message=message,
            code="SERVICE_ERROR",
            status_code=503
        )
        self.service = service
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.service:
            result["service"] = self.service
        return result


class RateLimitError(NexusError):
    """
    خطأ تجاوز الحد المسموح من الطلبات
    Rate limit exceeded error
    
    Attributes:
        message (str): رسالة الخطأ / Error message
        retry_after (int): عدد الثواني قبل إعادة المحاولة / Seconds before retry
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            status_code=429
        )
        self.retry_after = retry_after
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        return result


__all__ = [
    "NexusError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ConflictError",
    "DatabaseError",
    "ServiceError",
    "RateLimitError",
]
