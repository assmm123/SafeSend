"""
واجهات النظام - Protocols و Abstract Base Classes
System Interfaces - Protocols and Abstract Base Classes

هذا الملف يحتوي على تعريف الواجهات (العقود) التي يجب أن تنفذها الخدمات المختلفة.
This file contains interface definitions (contracts) that services must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID


# ============================================
# Repository Interfaces - واجهات المستودعات
# ============================================

@runtime_checkable
class IUserRepository(Protocol):
    """
    واجهة مستودع المستخدمين
    User Repository Interface
    
    تحدد العمليات الأساسية لإدارة المستخدمين في قاعدة البيانات.
    Defines basic operations for managing users in the database.
    """
    
    def get_by_id(self, user_id: UUID) -> Optional[Any]:
        """
        جلب مستخدم بواسطة المعرف
        Get user by ID
        
        Args:
            user_id (UUID): معرف المستخدم / User ID
            
        Returns:
            Optional[User]: المستخدم إذا وجد، None إذا لم يوجد
        """
        ...
    
    def get_by_email(self, email: str) -> Optional[Any]:
        """
        جلب مستخدم بواسطة البريد الإلكتروني
        Get user by email
        
        Args:
            email (str): البريد الإلكتروني / Email address
            
        Returns:
            Optional[User]: المستخدم إذا وجد، None إذا لم يوجد
        """
        ...
    
    def get_by_username(self, username: str) -> Optional[Any]:
        """
        جلب مستخدم بواسطة اسم المستخدم
        Get user by username
        
        Args:
            username (str): اسم المستخدم / Username
            
        Returns:
            Optional[User]: المستخدم إذا وجد، None إذا لم يوجد
        """
        ...
    
    def create(self, user: Any) -> Any:
        """
        إنشاء مستخدم جديد
        Create new user
        
        Args:
            user (User): كائن المستخدم / User object
            
        Returns:
            User: المستخدم المنشأ / Created user
        """
        ...
    
    def update(self, user: Any) -> Any:
        """
        تحديث بيانات مستخدم
        Update user data
        
        Args:
            user (User): كائن المستخدم مع التحديثات / User object with updates
            
        Returns:
            User: المستخدم المحدث / Updated user
        """
        ...
    
    def delete(self, user_id: UUID) -> bool:
        """
        حذف مستخدم (حذف ناعم)
        Soft delete user
        
        Args:
            user_id (UUID): معرف المستخدم / User ID
            
        Returns:
            bool: True إذا نجح الحذف / True if successful
        """
        ...
    
    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[Any]:
        """
        جلب قائمة المستخدمين
        List all users
        
        Args:
            skip (int): عدد العناصر للتخطي / Items to skip
            limit (int): الحد الأقصى للعناصر / Max items
            include_deleted (bool): تضمين المحذوفين / Include deleted users
            
        Returns:
            List[User]: قائمة المستخدمين / List of users
        """
        ...


@runtime_checkable
class IDealRepository(Protocol):
    """
    واجهة مستودع الصفقات
    Deal Repository Interface
    
    تحدد العمليات الأساسية لإدارة الصفقات في قاعدة البيانات.
    Defines basic operations for managing deals in the database.
    """
    
    def get_by_id(self, deal_id: UUID) -> Optional[Any]:
        """
        جلب صفقة بواسطة المعرف
        Get deal by ID
        """
        ...
    
    def get_by_buyer(self, buyer_id: UUID) -> List[Any]:
        """
        جلب صفقات المشتري
        Get deals by buyer
        """
        ...
    
    def get_by_seller(self, seller_id: UUID) -> List[Any]:
        """
        جلب صفقات البائع
        Get deals by seller
        """
        ...
    
    def create(self, deal: Any) -> Any:
        """
        إنشاء صفقة جديدة
        Create new deal
        """
        ...
    
    def update_status(self, deal_id: UUID, status: str) -> Any:
        """
        تحديث حالة الصفقة
        Update deal status
        """
        ...
    
    def list_by_status(self, status: str, limit: int = 100) -> List[Any]:
        """
        جلب الصفقات حسب الحالة
        List deals by status
        """
        ...


@runtime_checkable
class IAuditLogRepository(Protocol):
    """
    واجهة مستودع سجل التدقيق
    Audit Log Repository Interface
    """
    
    def log(
        self,
        user_id: Optional[UUID],
        action: str,
        resource: str,
        resource_id: Optional[str],
        old_value: Optional[Dict],
        new_value: Optional[Dict],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> Any:
        """
        تسجيل حدث في سجل التدقيق
        Log an audit event
        """
        ...
    
    def get_for_user(self, user_id: UUID, limit: int = 100) -> List[Any]:
        """
        جلب سجل التدقيق لمستخدم
        Get audit logs for a user
        """
        ...
    
    def get_for_resource(self, resource: str, resource_id: str) -> List[Any]:
        """
        جلب سجل التدقيق لمورد
        Get audit logs for a resource
        """
        ...


# ============================================
# Service Interfaces - واجهات الخدمات
# ============================================

@runtime_checkable
class ISecurityService(Protocol):
    """
    واجهة خدمة الأمان
    Security Service Interface
    
    توفر دوال التشفير والتحقق من كلمات المرور.
    Provides encryption and password verification functions.
    """
    
    def hash_password(self, password: str) -> str:
        """
        تشفير كلمة المرور
        Hash password
        
        Args:
            password (str): كلمة المرور النصية / Plain password
            
        Returns:
            str: كلمة المرور المشفرة / Hashed password
        """
        ...
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        التحقق من كلمة المرور
        Verify password
        
        Args:
            plain_password (str): كلمة المرور النصية / Plain password
            hashed_password (str): كلمة المرور المشفرة / Hashed password
            
        Returns:
            bool: True إذا تطابقت / True if match
        """
        ...
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        توليد توكن آمن
        Generate secure token
        
        Args:
            length (int): طول التوكن / Token length
            
        Returns:
            str: التوكن الآمن / Secure token
        """
        ...


@runtime_checkable
class ITokenService(Protocol):
    """
    واجهة خدمة التوكنات (JWT)
    Token Service Interface (JWT)
    """
    
    def generate(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """
        توليد توكن JWT
        Generate JWT token
        
        Args:
            payload (Dict): البيانات المراد تضمينها / Payload data
            expires_in (int): مدة الصلاحية بالثواني / Expiry in seconds
            
        Returns:
            str: التوكن / Token
        """
        ...
    
    def verify(self, token: str) -> Optional[Dict[str, Any]]:
        """
        التحقق من توكن JWT
        Verify JWT token
        
        Args:
            token (str): التوكن / Token
            
        Returns:
            Optional[Dict]: البيانات إذا كان صالحاً، None إذا غير صالح
        """
        ...
    
    def decode(self, token: str) -> Dict[str, Any]:
        """
        فك تشفير التوكن بدون تحقق
        Decode token without verification
        
        Args:
            token (str): التوكن / Token
            
        Returns:
            Dict: البيانات الموجودة في التوكن / Token payload
        """
        ...


@runtime_checkable
class IEmailService(Protocol):
    """
    واجهة خدمة البريد الإلكتروني
    Email Service Interface
    """
    
    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        إرسال بريد إلكتروني
        Send email
        
        Args:
            to_email (str): البريد المستلم / Recipient email
            subject (str): عنوان البريد / Email subject
            body (str): محتوى النص العادي / Plain text body
            html_body (Optional[str]): محتوى HTML / HTML body
            
        Returns:
            bool: True إذا تم الإرسال بنجاح / True if sent successfully
        """
        ...
    
    def send_verification(self, to_email: str, token: str) -> bool:
        """
        إرسال بريد تحقق
        Send verification email
        """
        ...
    
    def send_password_reset(self, to_email: str, token: str) -> bool:
        """
        إرسال بريد إعادة تعيين كلمة المرور
        Send password reset email
        """
        ...


@runtime_checkable
class ICacheService(Protocol):
    """
    واجهة خدمة التخزين المؤقت
    Cache Service Interface
    """
    
    def get(self, key: str) -> Optional[Any]:
        """
        جلب قيمة من التخزين المؤقت
        Get value from cache
        
        Args:
            key (str): المفتاح / Key
            
        Returns:
            Optional[Any]: القيمة إذا وجدت / Value if exists
        """
        ...
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        تخزين قيمة في التخزين المؤقت
        Set value in cache
        
        Args:
            key (str): المفتاح / Key
            value (Any): القيمة / Value
            ttl (int): مدة الصلاحية بالثواني / TTL in seconds
            
        Returns:
            bool: True إذا نجح التخزين / True if successful
        """
        ...
    
    def delete(self, key: str) -> bool:
        """
        حذف قيمة من التخزين المؤقت
        Delete value from cache
        
        Args:
            key (str): المفتاح / Key
            
        Returns:
            bool: True إذا نجح الحذف / True if successful
        """
        ...
    
    def exists(self, key: str) -> bool:
        """
        التحقق من وجود مفتاح
        Check if key exists
        
        Args:
            key (str): المفتاح / Key
            
        Returns:
            bool: True إذا وجد / True if exists
        """
        ...


@runtime_checkable
class IFileStorage(Protocol):
    """
    واجهة تخزين الملفات
    File Storage Interface
    """
    
    def upload(self, file_data: bytes, filename: str, content_type: str) -> str:
        """
        رفع ملف
        Upload file
        
        Args:
            file_data (bytes): بيانات الملف / File data
            filename (str): اسم الملف / Filename
            content_type (str): نوع المحتوى / Content type
            
        Returns:
            str: مسار الملف / File path
        """
        ...
    
    def download(self, file_path: str) -> Optional[bytes]:
        """
        تحميل ملف
        Download file
        
        Args:
            file_path (str): مسار الملف / File path
            
        Returns:
            Optional[bytes]: بيانات الملف / File data
        """
        ...
    
    def delete(self, file_path: str) -> bool:
        """
        حذف ملف
        Delete file
        
        Args:
            file_path (str): مسار الملف / File path
            
        Returns:
            bool: True إذا نجح الحذف / True if successful
        """
        ...
    
    def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        الحصول على رابط مؤقت للملف
        Get temporary URL for file
        
        Args:
            file_path (str): مسار الملف / File path
            expires_in (int): مدة الصلاحية بالثواني / Expiry in seconds
            
        Returns:
            str: الرابط المؤقت / Temporary URL
        """
        ...


# ============================================
# Abstract Base Classes - كلاسات مجردة
# ============================================

class BaseRepository(ABC):
    """
    كلاس أساسي مجرد لجميع المستودعات
    Abstract base class for all repositories
    """
    
    @abstractmethod
    def __init__(self, session: Any):
        """
        تهيئة المستودع مع جلسة قاعدة البيانات
        Initialize repository with database session
        """
        pass


class BaseService(ABC):
    """
    كلاس أساسي مجرد لجميع الخدمات
    Abstract base class for all services
    """
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        فحص صحة الخدمة
        Service health check
        
        Returns:
            Dict: حالة الخدمة / Service status
        """
        pass


__all__ = [
    # Repository Interfaces
    "IUserRepository",
    "IDealRepository",
    "IAuditLogRepository",
    # Service Interfaces
    "ISecurityService",
    "ITokenService",
    "IEmailService",
    "ICacheService",
    "IFileStorage",
    # Abstract Base Classes
    "BaseRepository",
    "BaseService",
]
