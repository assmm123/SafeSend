"""
نموذج المستخدم
User Model

يمثل المستخدمين في النظام مع دعم:
- تسجيل وتوثيق
- أدوار وصلاحيات
- حذف ناعم واستعادة
- قفل الحساب بعد محاولات فاشلة
- تتبع النشاط
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, JSON, String, Text
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


# ============================================
# الثوابت - Constants
# ============================================

class UserRole:
    """أدوار المستخدمين"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    SELLER = "seller"
    BUYER = "buyer"
    USER = "user"


ROLES = [UserRole.ADMIN, UserRole.MODERATOR, UserRole.SELLER, UserRole.BUYER, UserRole.USER]

MAX_FAILED_ATTEMPTS = 15
LOCK_TIMES = {5: 5, 10: 30, 15: 1440}  # محاولات -> دقائق قفل


# ============================================
# نموذج المستخدم - User Model
# ============================================

class User(BaseModel):
    """
    نموذج المستخدم
    User Model
    
    Attributes:
        email (str): البريد الإلكتروني (فريد)
        username (str): اسم المستخدم (فريد)
        password_hash (str): كلمة المرور المشفرة
        full_name (str): الاسم الكامل
        role (str): دور المستخدم
        is_active (bool): هل الحساب نشط؟
        deleted_at (datetime): تاريخ الحذف الناعم
    """
    
    __tablename__ = "users"
    
    # ============================================
    # المعلومات الأساسية
    # ============================================
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=False,
        doc="البريد الإلكتروني (فريد)"
    )
    
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=False,
        doc="اسم المستخدم (فريد)"
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="كلمة المرور المشفرة"
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="الاسم الكامل"
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="رقم الهاتف"
    )
    
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="رابط الصورة الرمزية"
    )
    
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="نبذة شخصية"
    )
    
    location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="الموقع"
    )
    
    website: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="الموقع الإلكتروني"
    )
    
    # ============================================
    # الحالة والتحقق
    # ============================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="هل الحساب نشط؟"
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل تم التحقق من البريد؟"
    )
    
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل البريد مؤكد؟"
    )
    
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="توكن التحقق من البريد"
    )
    
    email_verification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="تاريخ إرسال توكن التحقق"
    )
    
    # ============================================
    # الصلاحيات والأدوار
    # ============================================
    
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.USER,
        nullable=False,
        index=False,
        doc="دور المستخدم"
    )
    
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هو مدير؟ (للتوافق)"
    )
    
    permissions: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        doc="صلاحيات إضافية"
    )
    
    # ============================================
    # إعدادات المستخدم
    # ============================================
    
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc="إعدادات المستخدم (لغة، ثيم، إشعارات)"
    )
    
    # ============================================
    # الأمان وتتبع المحاولات
    # ============================================
    
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="محاولات تسجيل الدخول الفاشلة"
    )
    
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="تاريخ فك القفل"
    )
    
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="توكن إعادة تعيين كلمة المرور"
    )
    
    password_reset_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="تاريخ إرسال توكن إعادة التعيين"
    )
    
    # ============================================
    # تتبع النشاط
    # ============================================
    
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="آخر تسجيل دخول"
    )
    
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="آخر نشاط"
    )
    
    login_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد مرات تسجيل الدخول"
    )
    
    # ============================================
    # الحذف الناعم
    # ============================================
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=False,
        doc="تاريخ الحذف الناعم"
    )
    
    # ============================================
    # الفهارس - حسب القاعدة 1
    # ============================================
    
    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_username', 'username'),
        Index('ix_users_deleted_at', 'deleted_at'),
        Index('ix_users_role', 'role'),
        Index('ix_users_is_active', 'is_active'),
        Index('ix_users_email_verified', 'email_verified'),
        Index('ix_users_failed_attempts', 'failed_attempts'),
    )
    
    # ============================================
    # الخصائص - Properties
    # ============================================
    
    @property
    def is_deleted(self) -> bool:
        """هل المستخدم محذوف؟"""
        return self.deleted_at is not None
    
    @property
    def is_locked(self) -> bool:
        """هل الحساب مقفل؟"""
        if self.locked_until is None:
            return False
        if self.locked_until.tzinfo is None:
            self.locked_until = self.locked_until.replace(tzinfo=timezone.utc)
        return utc_now() < self.locked_until
    
    @property
    def is_profile_complete(self) -> bool:
        """هل الملف الشخصي مكتمل؟"""
        return self.full_name is not None and self.phone is not None
    
    # ============================================
    # دوال كلمة المرور
    # ============================================
    
    def set_password(self, password: str) -> None:
        """
        تشفير كلمة المرور
        Set password hash
        """
        from src.app.models.security import hash_password
        self.password_hash = hash_password(password)
    
    def check_password(self, password: str) -> bool:
        """
        التحقق من كلمة المرور
        Check password
        """
        from src.app.models.security import verify_password
        return verify_password(password, self.password_hash)
    
    # ============================================
    # دوال الحذف الناعم
    # ============================================
    
    def soft_delete(self) -> None:
        """حذف ناعم للمستخدم"""
        self.deleted_at = utc_now()
        self.is_active = False
    
    def restore(self) -> None:
        """استعادة المستخدم المحذوف"""
        self.deleted_at = None
        self.is_active = True  # هذا السطر مهم! (من مخاطر.txt)
    
    # ============================================
    # دوال قفل الحساب
    # ============================================
    
    def increment_failed_attempts(self) -> None:
        """زيادة محاولات الفشل وقفل الحساب إذا لزم"""
        self.failed_attempts += 1
        
        for attempts, lock_minutes in LOCK_TIMES.items():
            if self.failed_attempts == attempts:
                self.lock_account(minutes=lock_minutes)
                break
        
        if self.failed_attempts >= MAX_FAILED_ATTEMPTS:
            self.is_active = False
    
    def reset_failed_attempts(self) -> None:
        """إعادة تعيين محاولات الفشل"""
        self.failed_attempts = 0
        self.locked_until = None
    
    def lock_account(self, minutes: int = 30) -> None:
        """قفل الحساب لمدة محددة"""
        self.locked_until = utc_now() + timedelta(minutes=minutes)
    
    def unlock_account(self) -> None:
        """فك قفل الحساب"""
        self.locked_until = None
        self.failed_attempts = 0
    
    # ============================================
    # دوال تسجيل الدخول والنشاط
    # ============================================
    
    def record_login(self, ip_address: Optional[str] = None) -> None:
        """تسجيل دخول ناجح"""
        self.last_login = utc_now()
        self.last_activity_at = utc_now()
        self.login_count += 1
        self.reset_failed_attempts()
    
    def update_activity(self) -> None:
        """تحديث آخر نشاط"""
        self.last_activity_at = utc_now()
    
    # ============================================
    # دوال الصلاحيات والأدوار
    # ============================================
    
    def is_role_admin(self) -> bool:
        """هل المستخدم مدير؟"""
        return self.role == UserRole.ADMIN or bool(self.is_admin)
        """هل المستخدم مدير؟"""
        return self.role == UserRole.ADMIN or self.is_admin
        """هل المستخدم مدير؟"""
        return self.role == UserRole.ADMIN or self.is_admin
    
    def can_moderate(self) -> bool:
        """هل يمكنه الإشراف؟"""
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR]
    
    def can_sell(self) -> bool:
        """هل يمكنه البيع؟"""
        return self.role in [UserRole.ADMIN, UserRole.SELLER]
    
    def has_permission(self, permission: str) -> bool:
        """التحقق من صلاحية محددة"""
        if self.is_role_admin():
            return True
        if self.permissions and permission in self.permissions:
            return True
        return permission in self._get_default_permissions()
    
    def _get_default_permissions(self) -> List[str]:
        """الصلاحيات الافتراضية حسب الدور"""
        permissions_map = {
            UserRole.ADMIN: ["*"],
            UserRole.MODERATOR: ["users.read", "deals.moderate", "disputes.resolve"],
            UserRole.SELLER: ["deals.create", "deals.update_own", "deals.delete_own"],
            UserRole.BUYER: ["deals.view", "deals.buy", "messages.send"],
            UserRole.USER: ["profile.edit", "profile.view"],
        }
        return permissions_map.get(self.role, [])
    
    def grant_permission(self, permission: str) -> None:
        """منح صلاحية إضافية"""
        if self.permissions is None:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def revoke_permission(self, permission: str) -> None:
        """سحب صلاحية"""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)
    
    # ============================================
    # دوال التحقق من البريد
    # ============================================
    
    def generate_verification_token(self) -> str:
        """توليد توكن التحقق من البريد"""
        from src.app.models.security import generate_secure_token
        self.email_verification_token = generate_secure_token(32)
        self.email_verification_sent_at = utc_now()
        return self.email_verification_token
    
    def verify_email(self, token: str) -> bool:
        """التحقق من البريد الإلكتروني"""
        from src.app.models.security import constant_time_compare
        
        if self.email_verification_token is None:
            return False
        if self.email_verification_sent_at is None:
            return False
        
        # التوكن صالح لمدة 24 ساعة
        expiry = self.email_verification_sent_at + timedelta(hours=24)
        if utc_now() > expiry:
            return False
        
        if constant_time_compare(self.email_verification_token, token):
            self.email_verified = True
            self.is_verified = True
            self.email_verification_token = None
            return True
        
        return False
    
    # ============================================
    # دوال إعادة تعيين كلمة المرور
    # ============================================
    
    def generate_password_reset_token(self) -> str:
        """توليد توكن إعادة تعيين كلمة المرور"""
        from src.app.models.security import generate_secure_token
        self.password_reset_token = generate_secure_token(32)
        self.password_reset_sent_at = utc_now()
        return self.password_reset_token
    
    def verify_password_reset_token(self, token: str) -> bool:
        """التحقق من توكن إعادة التعيين"""
        from src.app.models.security import constant_time_compare
        
        if self.password_reset_token is None:
            return False
        if self.password_reset_sent_at is None:
            return False
        
        # التوكن صالح لمدة ساعة
        expiry = self.password_reset_sent_at + timedelta(hours=1)
        if utc_now() > expiry:
            return False
        
        return constant_time_compare(self.password_reset_token, token)
    
    def clear_password_reset_token(self) -> None:
        """مسح توكن إعادة التعيين"""
        self.password_reset_token = None
        self.password_reset_sent_at = None
    
    # ============================================
    # دوال الإعدادات
    # ============================================
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """جلب إعداد"""
        if self.preferences is None:
            return default
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """تعيين إعداد"""
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def to_public_dict(self) -> Dict[str, Any]:
        """
        تحويل المستخدم إلى قاموس للمعلومات العامة
        (بدون بيانات حساسة)
        """
        return {
            "id": str(self.id),
            "username": self.username,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "location": self.location,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """تحويل المستخدم إلى قاموس كامل"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "location": self.location,
            "website": self.website,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "email_verified": self.email_verified,
            "is_deleted": self.is_deleted,
            "is_locked": self.is_locked,
            "failed_attempts": self.failed_attempts,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "login_count": self.login_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data["preferences"] = self.preferences
            data["permissions"] = self.permissions
        
        return data
    
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


__all__ = [
    "User",
    "UserRole",
    "ROLES",
    "MAX_FAILED_ATTEMPTS",
    "LOCK_TIMES",
]
