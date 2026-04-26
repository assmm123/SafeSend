"""
نموذج الجلسات
Session Model

يدير جلسات المستخدمين مع دعم:
- تتبع الأجهزة والمواقع
- Refresh Tokens
- انتهاء الصلاحية
- إبطال الجلسات
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, JSON, String, Text
)
from sqlalchemy.orm import Mapped, Session, relationship, mapped_column

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


# ============================================
# الثوابت - Constants
# ============================================

class DeviceType:
    """أنواع الأجهزة"""
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"
    API = "api"
    BOT = "bot"
    UNKNOWN = "unknown"


class SessionStatus:
    """حالات الجلسة"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOGGED_OUT = "logged_out"


# مدة الصلاحية حسب نوع الجهاز (بالأيام)
DEVICE_EXPIRY_DAYS = {
    DeviceType.WEB: 7,
    DeviceType.MOBILE: 30,
    DeviceType.DESKTOP: 14,
    DeviceType.TABLET: 30,
    DeviceType.API: 1,
    DeviceType.UNKNOWN: 7,
}


# ============================================
# دوال مساعدة - Helper Functions
# ============================================

def parse_user_agent(user_agent: str) -> Dict[str, Any]:
    """
    تحليل User-Agent لاستخراج معلومات الجهاز
    Parse User-Agent to extract device information
    
    Args:
        user_agent (str): نص User-Agent
    
    Returns:
        Dict: معلومات الجهاز
    """
    result = {
        "browser": "Unknown",
        "browser_version": "",
        "os": "Unknown",
        "os_version": "",
        "device": DeviceType.UNKNOWN,
        "is_mobile": False,
        "is_tablet": False,
        "is_bot": False,
        "raw": user_agent[:500] if user_agent else "",
    }
    
    if not user_agent:
        return result
    
    ua = user_agent.lower()
    
    # كشف البوتات
    bots = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python', 'java']
    for bot in bots:
        if bot in ua:
            result['is_bot'] = True
            result['device'] = DeviceType.BOT
            result['browser'] = 'Bot'
            return result
    
    # كشف المتصفح
    if 'edg/' in ua:
        result['browser'] = 'Edge'
        match = re.search(r'edg/(\d+)', ua)
        if match:
            result['browser_version'] = match.group(1)
    elif 'firefox' in ua:
        result['browser'] = 'Firefox'
        match = re.search(r'firefox/(\d+)', ua)
        if match:
            result['browser_version'] = match.group(1)
    elif 'chrome' in ua:
        result['browser'] = 'Chrome'
        match = re.search(r'chrome/(\d+)', ua)
        if match:
            result['browser_version'] = match.group(1)
    elif 'safari' in ua and 'chrome' not in ua:
        result['browser'] = 'Safari'
        match = re.search(r'version/(\d+\.\d+)', ua)
        if match:
            result['browser_version'] = match.group(1)
    elif 'opera' in ua or 'opr/' in ua:
        result['browser'] = 'Opera'
    
    # كشف نظام التشغيل
    if 'android' in ua:
        result['os'] = 'Android'
        result['is_mobile'] = True
        match = re.search(r'android (\d+(\.\d+)?)', ua)
        if match:
            result['os_version'] = match.group(1)
        if 'tablet' in ua or 'tab' in ua:
            result['is_tablet'] = True
            result['device'] = DeviceType.TABLET
        else:
            result['device'] = DeviceType.MOBILE
    elif 'iphone' in ua:
        result['os'] = 'iOS'
        result['is_mobile'] = True
        result['device'] = DeviceType.MOBILE
    elif 'ipad' in ua:
        result['os'] = 'iOS'
        result['is_tablet'] = True
        result['device'] = DeviceType.TABLET
    elif 'windows nt' in ua:
        result['os'] = 'Windows'
        result['device'] = DeviceType.DESKTOP
        match = re.search(r'windows nt (\d+\.\d+)', ua)
        if match:
            result['os_version'] = match.group(1)
    elif 'mac os x' in ua:
        result['os'] = 'macOS'
        result['device'] = DeviceType.DESKTOP
    elif 'linux' in ua:
        result['os'] = 'Linux'
        result['device'] = DeviceType.DESKTOP
    
    # كشف API clients
    if 'postman' in ua or 'insomnia' in ua or 'curl' in ua:
        result['device'] = DeviceType.API
    
    return result


def generate_device_fingerprint(user_agent: str, ip_address: str) -> str:
    """
    توليد بصمة للجهاز
    Generate device fingerprint
    
    Args:
        user_agent (str): User-Agent
        ip_address (str): عنوان IP
    
    Returns:
        str: بصمة الجهاز
    """
    data = f"{user_agent}|{ip_address}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


# ============================================
# نموذج الجلسة - Session Model
# ============================================

class Session(BaseModel):
    """
    نموذج الجلسة
    Session Model
    
    Attributes:
        user_id (UUID): معرف المستخدم
        refresh_token (str): توكن التحديث
        ip_address (str): عنوان IP
        device_info (dict): معلومات الجهاز
        expires_at (datetime): تاريخ انتهاء الجلسة
        is_active (bool): هل الجلسة نشطة؟
    """
    
    __tablename__ = "sessions"
    
    # ============================================
    # العلاقات
    # ============================================
    
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=False,
        doc="معرف المستخدم"
    )
    
    # علاقة أحادية الاتجاه (حسب القاعدة 3)
    user = relationship('User')
    
    # ============================================
    # التوكنات
    # ============================================
    
    refresh_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=False,
        doc="توكن التحديث"
    )
    
    access_token: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="توكن الوصول الحالي"
    )
    
    # ============================================
    # معلومات الجهاز والموقع
    # ============================================
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="عنوان IP"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User-Agent"
    )
    
    device_info: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc="معلومات الجهاز"
    )
    
    device_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="بصمة الجهاز"
    )
    
    location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="الموقع الجغرافي"
    )
    
    # ============================================
    # الحالة والصلاحية
    # ============================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="هل الجلسة نشطة؟"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        default=SessionStatus.ACTIVE,
        nullable=False,
        doc="حالة الجلسة"
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="تاريخ انتهاء الجلسة"
    )
    
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: utc_now(),
        nullable=False,
        doc="آخر نشاط"
    )
    
    # ============================================
    # الإبطال
    # ============================================
    
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=False,
        doc="تاريخ الإبطال"
    )
    
    revoke_reason: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="سبب الإبطال"
    )
    
    # ============================================
    # بيانات إضافية
    # ============================================
    
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc="بيانات إضافية"
    )
    
    # ============================================
    # الفهارس - حسب القاعدة 1
    # ============================================
    
    __table_args__ = (
        Index('ix_sessions_user_id', 'user_id'),
        Index('ix_sessions_refresh_token', 'refresh_token'),
        Index('ix_sessions_expires_at', 'expires_at'),
        Index('ix_sessions_is_active', 'is_active'),
        Index('ix_sessions_status', 'status'),
        Index('ix_sessions_device_fingerprint', 'device_fingerprint'),
        Index('ix_sessions_revoked_at', 'revoked_at'),
    )
    
    # ============================================
    # دوال التهيئة
    # ============================================
    
    def __init__(self, **kwargs):
        """تهيئة الجلسة مع استخراج معلومات الجهاز"""
        super().__init__(**kwargs)
        
        if self.device_info is None:
            self.device_info = {}
        if self.user_agent and not self.device_info:
            self.device_info = parse_user_agent(self.user_agent)
        
        if self.user_agent and self.ip_address and not self.device_fingerprint:
            self.device_fingerprint = generate_device_fingerprint(
                self.user_agent, self.ip_address
            )
        
        if not self.expires_at:
            device_type = self.device_info.get('device', DeviceType.UNKNOWN)
            days = DEVICE_EXPIRY_DAYS.get(device_type, 7)
            self.expires_at = utc_now() + timedelta(days=days)
    
    # ============================================
    # الخصائص - Properties
    # ============================================
    
    @property
    def is_expired(self) -> bool:
        """هل انتهت الجلسة؟"""
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return utc_now() > self.expires_at
    
    @property
    def is_revoked(self) -> bool:
        """هل الجلسة مبطلّة؟"""
        return self.revoked_at is not None
    
    @property
    def is_valid(self) -> bool:
        """هل الجلسة صالحة؟"""
        return self.is_active and not self.is_expired and not self.is_revoked
    
    @property
    def device_type(self) -> str:
        """نوع الجهاز"""
        if self.device_info:
            return self.device_info.get('device', DeviceType.UNKNOWN)
        return DeviceType.UNKNOWN
    
    @property
    def browser_name(self) -> str:
        """اسم المتصفح"""
        if self.device_info:
            return self.device_info.get('browser', 'Unknown')
        return 'Unknown'
    
    @property
    def os_name(self) -> str:
        """نظام التشغيل"""
        if self.device_info:
            return self.device_info.get('os', 'Unknown')
        return 'Unknown'
    
    # ============================================
    # دوال التوكنات
    # ============================================
    
    def generate_refresh_token(self) -> str:
        """
        توليد Refresh Token جديد
        Generate new refresh token
        """
        from src.app.models.security import generate_secure_token
        self.refresh_token = generate_secure_token(64)
        return self.refresh_token
    
    def set_access_token(self, token: str) -> None:
        """تعيين Access Token"""
        self.access_token = token
    
    def verify_refresh_token(self, token: str) -> bool:
        """
        التحقق من Refresh Token
        Verify refresh token
        """
        from src.app.models.security import constant_time_compare
        return constant_time_compare(self.refresh_token, token)
    
    # ============================================
    # دوال الحالة
    # ============================================
    
    def update_activity(self) -> None:
        """تحديث آخر نشاط"""
        self.last_activity_at = utc_now()
    
    def refresh_expiry(self, days: Optional[int] = None) -> None:
        """
        تمديد صلاحية الجلسة
        Extend session expiry
        """
        if days is None:
            days = DEVICE_EXPIRY_DAYS.get(self.device_type, 7)
        self.expires_at = utc_now() + timedelta(days=days)
    
    def revoke(self, reason: str = 'manual') -> None:
        """
        إبطال الجلسة
        Revoke session
        
        Args:
            reason (str): سبب الإبطال
        """
        self.is_active = False
        self.status = SessionStatus.REVOKED
        self.revoked_at = utc_now()
        self.revoke_reason = reason
    
    def logout(self) -> None:
        """تسجيل خروج (إبطال مع سبب logout)"""
        self.revoke(reason='logout')
        self.status = SessionStatus.LOGGED_OUT
    
    def expire(self) -> None:
        """تعليم الجلسة كمنتهية"""
        self.status = SessionStatus.EXPIRED
        self.is_active = False
    
    # ============================================
    # دوال معلومات الجهاز
    # ============================================
    
    def set_device_info(self, user_agent: str) -> None:
        """استخراج وتعيين معلومات الجهاز"""
        self.user_agent = user_agent
        self.device_info = parse_user_agent(user_agent)
        if self.ip_address:
            self.device_fingerprint = generate_device_fingerprint(user_agent, self.ip_address)
    
    def set_location(self, location: str) -> None:
        """تعيين الموقع الجغرافي"""
        self.location = location
    
    def is_new_device(self, session: Session) -> bool:
        """
        هل هذا جهاز جديد للمستخدم؟
        Is this a new device for the user?
        """
        if not self.device_fingerprint:
            return True
        
        existing = session.query(Session).filter(
            Session.user_id == self.user_id,
            Session.device_fingerprint == self.device_fingerprint,
            Session.id != self.id
        ).first()
        
        return existing is None
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """تحويل الجلسة إلى قاموس"""
        data = {
            "id": str(self.id),
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "location": self.location,
            "is_active": self.is_active,
            "status": self.status,
            "is_valid": self.is_valid,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "device_type": self.device_type,
            "browser": self.browser_name,
            "os": self.os_name,
        }
        
        if include_sensitive:
            data["refresh_token"] = self.refresh_token
            data["access_token"] = self.access_token
            data["device_fingerprint"] = self.device_fingerprint
        
        if self.revoked_at:
            data["revoked_at"] = self.revoked_at.isoformat()
            data["revoke_reason"] = self.revoke_reason
        
        return data
    
    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} device={self.device_type}>"


# ============================================
# دوال على مستوى الكلاس - Class Methods
# ============================================

class SessionManager:
    """مدير الجلسات - دوال مساعدة على مستوى الكلاس"""
    
    @staticmethod
    def create_session(
        session: Session,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> 'Session':
        """
        إنشاء جلسة جديدة
        Create new session
        """
        sess = Session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        sess.generate_refresh_token()
        session.add(sess)
        session.flush()
        return sess
    
    @staticmethod
    def find_by_refresh_token(session: Session, token: str) -> Optional['Session']:
        """البحث عن جلسة بواسطة refresh token"""
        return session.query(Session).filter(
            Session.refresh_token == token
        ).first()
    
    @staticmethod
    def find_active_by_user(session: Session, user_id: str) -> List['Session']:
        """جلب الجلسات النشطة للمستخدم"""
        return session.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True,
            Session.revoked_at == None
        ).all()
    
    @staticmethod
    def get_active_count(session: Session, user_id: str) -> int:
        """عدد الجلسات النشطة للمستخدم"""
        return session.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True,
            Session.revoked_at == None
        ).count()
    
    @staticmethod
    def revoke_all_user_sessions(
        session: Session,
        user_id: str,
        reason: str = 'logout_all',
        exclude_session_id: Optional[str] = None
    ) -> int:
        """
        إبطال جميع جلسات المستخدم
        Revoke all user sessions
        """
        query = session.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True
        )
        
        if exclude_session_id:
            query = query.filter(Session.id != exclude_session_id)
        
        count = query.update({
            'is_active': False,
            'status': SessionStatus.REVOKED,
            'revoked_at': utc_now(),
            'revoke_reason': reason
        })
        
        return count
    
    @staticmethod
    def cleanup_expired_sessions(session: Session, days_old: int = 30) -> int:
        """
        تنظيف الجلسات المنتهية
        Cleanup expired sessions
        """
        cutoff = utc_now() - timedelta(days=days_old)
        
        # حذف الجلسات المنتهية أو المبطلّة القديمة
        deleted = session.query(Session).filter(
            (Session.expires_at < cutoff) |
            ((Session.revoked_at != None) & (Session.revoked_at < cutoff))
        ).delete()
        
        return deleted
    
    @staticmethod
    def count_by_device_type(session: Session, user_id: str) -> Dict[str, int]:
        """إحصاء الجلسات حسب نوع الجهاز"""
        result = {}
        sessions = session.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True
        ).all()
        
        for sess in sessions:
            device = sess.device_type
            result[device] = result.get(device, 0) + 1
        
        return result
    
    @staticmethod
    def get_user_devices(session: Session, user_id: str) -> List[Dict[str, Any]]:
        """جلب قائمة أجهزة المستخدم (بدون تكرار)"""
        devices = {}
        sessions = session.query(Session).filter(
            Session.user_id == user_id
        ).order_by(Session.last_activity_at.desc()).all()
        
        for sess in sessions:
            fingerprint = sess.device_fingerprint
            if fingerprint and fingerprint not in devices:
                devices[fingerprint] = {
                    "fingerprint": fingerprint,
                    "device_type": sess.device_type,
                    "browser": sess.browser_name,
                    "os": sess.os_name,
                    "last_activity": sess.last_activity_at.isoformat() if sess.last_activity_at else None,
                    "is_active": sess.is_valid,
                    "location": sess.location,
                }
        
        return list(devices.values())


__all__ = [
    "Session",
    "SessionManager",
    "DeviceType",
    "SessionStatus",
    "DEVICE_EXPIRY_DAYS",
    "parse_user_agent",
    "generate_device_fingerprint",
]
