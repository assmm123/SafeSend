"""
نموذج المستخدم
User Model

يمثل المستخدمين في النظام مع دعم:
- تسجيل وتوثيق
- أدوار وصلاحيات
- حذف ناعم واستعادة
- قفل الحساب بعد محاولات فاشلة
- تتبع النشاط
- مصادقة ثنائية (2FA)
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
BACKUP_CODES_COUNT = 8  # عدد الرموز الاحتياطية


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
        is_2fa_enabled (bool): هل المصادقة الثنائية مفعلة؟
        encrypted_2fa_secret (str): مفتاح TOTP مشفر
        backup_codes (list): رموز احتياطية مشفرة
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
    
    permissions: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        doc="صلاحيات إضافية"
    )
    
    # ============================================
    # إعدادات المستخدم
    # ============================================
    
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
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
    # المصادقة الثنائية - Two-Factor Authentication
    # ============================================
    
    is_2fa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل المصادقة الثنائية مفعلة؟"
    )
    
    encrypted_2fa_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="مفتاح TOTP مشفر"
    )
    
    backup_codes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        doc="رموز احتياطية مشفرة (للاستخدام لمرة واحدة)"
    )
    
    used_backup_codes_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد الرموز الاحتياطية المستخدمة"
    )
    
    two_fa_enabled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="تاريخ تفعيل المصادقة الثنائية"
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
    
    @property
    def remaining_backup_codes(self) -> int:
        """عدد الرموز الاحتياطية المتبقية"""
        if self.backup_codes is None:
            return 0
        return len(self.backup_codes)
    
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
        self.is_active = True
    
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
    # دوال المصادقة الثنائية - 2FA Methods
    # ============================================
    
    def setup_2fa(self, secret: str) -> str:
        """
        تفعيل إعداد المصادقة الثنائية
        Set up 2FA with encrypted secret
        Returns provisioning URI for QR code
        """
        import pyotp
        from src.app.models.security import encrypt_data
        
        self.encrypted_2fa_secret = encrypt_data(secret)
        self.is_2fa_enabled = True
        self.two_fa_enabled_at = utc_now()
        
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name="SafeSend"
        )
    
    def disable_2fa(self) -> None:
        """
        تعطيل المصادقة الثنائية
        Disable 2FA and clear all related data
        """
        self.encrypted_2fa_secret = None
        self.backup_codes = None
        self.is_2fa_enabled = False
        self.used_backup_codes_count = 0
        self.two_fa_enabled_at = None
    
    def get_2fa_secret(self) -> Optional[str]:
        """
        استرجاع مفتاح 2FA بعد فك التشفير
        Get decrypted 2FA secret
        """
        if not self.encrypted_2fa_secret:
            return None
        from src.app.models.security import decrypt_data
        try:
            return decrypt_data(self.encrypted_2fa_secret)
        except Exception:
            return None
    
    def verify_2fa_code(self, code: str) -> bool:
        """
        التحقق من رمز 2FA باستخدام TOTP حقيقي
        Verify 2FA code using real TOTP
        """
        import pyotp
        
        if not self.is_2fa_enabled:
            return False
        
        secret = self.get_2fa_secret()
        if not secret:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code)
        except Exception:
            return False
    
    def set_backup_codes(self, codes: list) -> None:
        """
        تعيين الرموز الاحتياطية (تشفيرها قبل التخزين)
        Set encrypted backup codes
        """
        from src.app.models.security import encrypt_data
        encrypted = [encrypt_data(str(code)) for code in codes]
        self.backup_codes = encrypted
        self.used_backup_codes_count = 0
    
    def verify_backup_code(self, code: str) -> bool:
        """
        التحقق من رمز احتياطي (استخدام مرة واحدة)
        Verify a backup code - one-time use only
        """
        from src.app.models.security import decrypt_data, constant_time_compare
        
        if not self.backup_codes:
            return False
        
        for i, encrypted_code in enumerate(self.backup_codes):
            try:
                decrypted = decrypt_data(encrypted_code)
                if constant_time_compare(decrypted, str(code)):
                    # إزالة الرمز المستخدم (استخدام مرة واحدة)
                    self.backup_codes.pop(i)
                    self.used_backup_codes_count += 1
                    return True
            except Exception:
                continue
        
        return False
    
    def generate_2fa_qr_code(self, issuer: str = "SafeSend") -> Optional[str]:
        """
        توليد QR code للمصادقة الثنائية بصيغة base64
        Generate QR code for 2FA setup as base64 PNG
        """
        import qrcode
        import io
        import base64
        import pyotp
        
        secret = self.get_2fa_secret()
        if not secret:
            return None
        
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=self.email, issuer_name=issuer)
        
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # ============================================
    # دوال الإعدادات - Preferences M
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
            "is_2fa_enabled": self.is_2fa_enabled,
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
            "is_2fa_enabled": self.is_2fa_enabled,
            "is_deleted": self.is_deleted,
            "is_locked": self.is_locked,
            "failed_attempts": self.failed_attempts,
            "remaining_backup_codes": self.remaining_backup_codes,
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
        return f"<User id={self.id} email={self.email} role={self.role} 2fa={self.is_2fa_enabled}>"


__all__ = [
    "User",
    "UserRole",
    "ROLES",
    "MAX_FAILED_ATTEMPTS",
    "LOCK_TIMES",
    "BACKUP_CODES_COUNT",
]
