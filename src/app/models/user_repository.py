"""
مستودع المستخدم
User Repository

نمط Repository لعزل عمليات قاعدة البيانات عن منطق الأعمال
ينفذ IUserRepository من interfaces.py
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.app.models.user import User, UserRole, ROLES
from src.app.models.session import Session as UserSession
from src.app.models.interfaces import IUserRepository
from src.app.models.helpers import utc_now
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# Pagination Result
# ============================================

@dataclass
class PaginatedResult:
    """نتيجة التصفح"""
    items: List[User]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


# ============================================
# User Repository
# ============================================

class UserRepository(IUserRepository):
    """
    مستودع المستخدم
    User Repository
    
    يغلف جميع عمليات قاعدة البيانات المتعلقة بالمستخدمين
    """
    
    def __init__(self, session: Session):
        """
        تهيئة المستودع مع جلسة قاعدة البيانات
        
        Args:
            session (Session): جلسة SQLAlchemy
        """
        self.session = session
    
    # ============================================
    # عمليات القراءة
    # ============================================
    
    def get_by_id(self, user_id) -> Optional[User]:
        import uuid
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        """جلب مستخدم بواسطة المعرف"""
        return self.session.query(User).filter(
            User.id == user_id,
            User.deleted_at == None
        ).first()
    
    def get_by_id_include_deleted(self, user_id: UUID) -> Optional[User]:
        """جلب مستخدم بواسطة المعرف (يشمل المحذوفين)"""
        return self.session.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """جلب مستخدم بواسطة البريد الإلكتروني"""
        return self.session.query(User).filter(
            func.lower(User.email) == email.lower(),
            User.deleted_at == None
        ).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """جلب مستخدم بواسطة اسم المستخدم"""
        return self.session.query(User).filter(
            func.lower(User.username) == username.lower(),
            User.deleted_at == None
        ).first()
    
    def get_by_email_verification_token(self, token: str) -> Optional[User]:
        """جلب مستخدم بواسطة توكن التحقق من البريد"""
        return self.session.query(User).filter(
            User.email_verification_token == token,
            User.deleted_at == None
        ).first()
    
    def get_by_password_reset_token(self, token: str) -> Optional[User]:
        """جلب مستخدم بواسطة توكن إعادة تعيين كلمة المرور"""
        return self.session.query(User).filter(
            User.password_reset_token == token,
            User.deleted_at == None
        ).first()
    
    def exists_by_email(self, email: str) -> bool:
        """التحقق من وجود بريد إلكتروني"""
        return self.session.query(User).filter(
            func.lower(User.email) == email.lower()
        ).first() is not None
    
    def exists_by_username(self, username: str) -> bool:
        """التحقق من وجود اسم مستخدم"""
        return self.session.query(User).filter(
            func.lower(User.username) == username.lower()
        ).first() is not None
    
    # ============================================
    # القوائم والتصفح
    # ============================================
    
    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[User]:
        """
        جلب قائمة المستخدمين مع تصفية متقدمة
        
        Args:
            skip (int): عدد العناصر للتخطي
            limit (int): الحد الأقصى للعناصر
            include_deleted (bool): تضمين المحذوفين
            role (Optional[str]): تصفية حسب الدور
            is_active (Optional[bool]): تصفية حسب النشاط
            is_verified (Optional[bool]): تصفية حسب التحقق
            order_by (str): ترتيب حسب
            order_desc (bool): ترتيب تنازلي
            
        Returns:
            List[User]: قائمة المستخدمين
        """
        query = self.session.query(User)
        
        if not include_deleted:
            query = query.filter(User.deleted_at == None)
        
        if role:
            query = query.filter(User.role == role)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if is_verified is not None:
            query = query.filter(User.is_verified == is_verified)
        
        order_column = getattr(User, order_by, User.created_at)
        if order_desc:
            order_column = order_column.desc()
        
        return query.order_by(order_column).offset(skip).limit(limit).all()
    
    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> PaginatedResult:
        """
        تصفح المستخدمين مع Pagination
        
        Args:
            page (int): رقم الصفحة
            page_size (int): حجم الصفحة
            include_deleted (bool): تضمين المحذوفين
            role (Optional[str]): تصفية حسب الدور
            is_active (Optional[bool]): تصفية حسب النشاط
            search (Optional[str]): بحث في البريد أو الاسم
            
        Returns:
            PaginatedResult: نتيجة التصفح
        """
        query = self.session.query(User)
        
        if not include_deleted:
            query = query.filter(User.deleted_at == None)
        
        if role:
            query = query.filter(User.role == role)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if search:
            query = query.filter(
                (User.email.contains(search)) |
                (User.username.contains(search)) |
                (User.full_name.contains(search))
            )
        
        total = query.count()
        items = query.order_by(User.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
    
    def search(self, query: str, limit: int = 50) -> List[User]:
        """
        البحث عن مستخدمين
        
        Args:
            query (str): عبارة البحث
            limit (int): الحد الأقصى للنتائج
            
        Returns:
            List[User]: قائمة المستخدمين
        """
        return self.session.query(User).filter(
            User.deleted_at == None,
            (
                User.email.contains(query) |
                User.username.contains(query) |
                User.full_name.contains(query)
            )
        ).limit(limit).all()
    
    def get_by_role(self, role: str, limit: int = 100) -> List[User]:
        """جلب المستخدمين حسب الدور"""
        return self.session.query(User).filter(
            User.role == role,
            User.deleted_at == None
        ).limit(limit).all()
    
    def get_admins(self) -> List[User]:
        """جلب جميع المدراء"""
        return self.session.query(User).filter(
            (User.role == UserRole.ADMIN) | (User.is_admin == True),
            User.deleted_at == None
        ).all()
    
    # ============================================
    # الإحصائيات
    # ============================================
    
    def count(
        self,
        include_deleted: bool = False,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> int:
        """عدد المستخدمين"""
        query = self.session.query(User)
        
        if not include_deleted:
            query = query.filter(User.deleted_at == None)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if role:
            query = query.filter(User.role == role)
        
        return query.count()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        إحصائيات المستخدمين
        
        Returns:
            Dict: إحصائيات المستخدمين
        """
        return {
            "total": self.count(),
            "active": self.count(is_active=True),
            "inactive": self.count(is_active=False),
            "verified": self.session.query(User).filter(
                User.is_verified == True,
                User.deleted_at == None
            ).count(),
            "deleted": self.count(include_deleted=True) - self.count(),
            "locked": self.session.query(User).filter(
                User.locked_until > utc_now()
            ).count(),
            "by_role": {
                role: self.count(role=role)
                for role in ROLES
            },
            "new_today": self.session.query(User).filter(
                User.created_at >= utc_now().replace(hour=0, minute=0, second=0)
            ).count(),
        }
    
    # ============================================
    # عمليات الكتابة
    # ============================================
    
    def create(self, user: User) -> User:
        """
        إنشاء مستخدم جديد
        
        Args:
            user (User): كائن المستخدم
            
        Returns:
            User: المستخدم المنشأ
        """
        self.session.add(user)
        self.session.flush()
        logger.info(f"User created: {user.email}")
        return user
    
    def update(self, user: User) -> User:
        """
        تحديث مستخدم
        
        Args:
            user (User): كائن المستخدم مع التحديثات
            
        Returns:
            User: المستخدم المحدث
        """
        user.updated_at = utc_now()
        self.session.flush()
        logger.info(f"User updated: {user.id}")
        return user
    
    def delete(self, user_id: UUID, soft: bool = True) -> bool:
        """
        حذف مستخدم
        
        Args:
            user_id (UUID): معرف المستخدم
            soft (bool): حذف ناعم (افتراضي) أو حذف نهائي
            
        Returns:
            bool: True إذا نجح الحذف
        """
        user = self.get_by_id_include_deleted(user_id)
        if not user:
            return False
        
        if soft:
            user.soft_delete()
            logger.info(f"User soft deleted: {user_id}")
        else:
            self.session.delete(user)
            logger.info(f"User hard deleted: {user_id}")
        
        self.session.flush()
        return True
    
    def restore(self, user_id: UUID) -> bool:
        """
        استعادة مستخدم محذوف
        
        Args:
            user_id (UUID): معرف المستخدم
            
        Returns:
            bool: True إذا نجحت الاستعادة
        """
        user = self.get_by_id_include_deleted(user_id)
        if not user or not user.is_deleted:
            return False
        
        user.restore()
        self.session.flush()
        logger.info(f"User restored: {user_id}")
        return True
    
    def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        تغيير كلمة مرور المستخدم
        
        Args:
            user_id (UUID): معرف المستخدم
            new_password (str): كلمة المرور الجديدة
            
        Returns:
            bool: True إذا نجح التغيير
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.set_password(new_password)
        user.clear_password_reset_token()
        self.session.flush()
        logger.info(f"Password changed for user: {user_id}")
        return True
    
    def verify_email(self, user_id: UUID, token: str) -> bool:
        """
        التحقق من البريد الإلكتروني
        
        Args:
            user_id (UUID): معرف المستخدم
            token (str): توكن التحقق
            
        Returns:
            bool: True إذا نجح التحقق
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        success = user.verify_email(token)
        if success:
            self.session.flush()
            logger.info(f"Email verified for user: {user_id}")
        return success
    
    def record_login(self, user_id: UUID, ip_address: Optional[str] = None) -> bool:
        """
        تسجيل دخول ناجح
        
        Args:
            user_id (UUID): معرف المستخدم
            ip_address (Optional[str]): عنوان IP
            
        Returns:
            bool: True إذا نجح التسجيل
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.record_login(ip_address)
        self.session.flush()
        return True
    
    def record_failed_attempt(self, user_id: UUID) -> bool:
        """
        تسجيل محاولة دخول فاشلة
        
        Args:
            user_id (UUID): معرف المستخدم
            
        Returns:
            bool: True إذا نجح التسجيل
        """
        user = self.get_by_id_include_deleted(user_id)
        if not user:
            return False
        
        user.increment_failed_attempts()
        self.session.flush()
        return True
    
    # ============================================
    # عمليات Bulk
    # ============================================
    
    def bulk_create(self, users: List[User]) -> List[User]:
        """إنشاء عدة مستخدمين دفعة واحدة"""
        self.session.add_all(users)
        self.session.flush()
        logger.info(f"Bulk created {len(users)} users")
        return users
    
    def bulk_update_status(self, user_ids: List[UUID], is_active: bool) -> int:
        """تحديث حالة عدة مستخدمين"""
        count = self.session.query(User).filter(
            User.id.in_(user_ids)
        ).update(
            {"is_active": is_active, "updated_at": utc_now()},
            synchronize_session="fetch"
        )
        self.session.flush()
        logger.info(f"Bulk updated {count} users status to active={is_active}")
        return count
    
    def bulk_delete(self, user_ids: List[UUID], soft: bool = True) -> int:
        """حذف عدة مستخدمين"""
        if soft:
            count = self.session.query(User).filter(
                User.id.in_(user_ids)
            ).update(
                {"deleted_at": utc_now(), "is_active": False},
                synchronize_session="fetch"
            )
        else:
            count = self.session.query(User).filter(
                User.id.in_(user_ids)
            ).delete(synchronize_session="fetch")
        
        self.session.flush()
        logger.info(f"Bulk deleted {count} users (soft={soft})")
        return count
    
    # ============================================
    # الجلسات
    # ============================================
    
    def get_active_sessions(self, user_id: UUID) -> List[UserSession]:
        """جلب الجلسات النشطة للمستخدم"""
        return self.session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.revoked_at == None,
            UserSession.expires_at > utc_now()
        ).all()
    
    def revoke_all_sessions(self, user_id: UUID, exclude_session_id: Optional[str] = None) -> int:
        """إبطال جميع جلسات المستخدم"""
        from src.app.models.session import SessionManager
        return SessionManager.revoke_all_user_sessions(
            self.session, str(user_id), exclude_session_id=exclude_session_id
        )
    
    # ============================================
    # مساعدة
    # ============================================
    
    def generate_verification_token(self, user_id: UUID) -> Optional[str]:
        """توليد توكن التحقق من البريد"""
        user = self.get_by_id(user_id)
        if not user:
            return None
        token = user.generate_verification_token()
        self.session.flush()
        return token
    
    def generate_password_reset_token(self, email: str) -> Optional[str]:
        """توليد توكن إعادة تعيين كلمة المرور"""
        user = self.get_by_email(email)
        if not user:
            return None
        token = user.generate_password_reset_token()
        self.session.flush()
        return token




# ============================================
# Helper - Get Repository with DB Session
# ============================================

def get_user_repo():
    """Get UserRepository instance with database session."""
    from src.app.models.database import get_db
    db = next(get_db())
    return UserRepository(db)


__all__ = [
    "UserRepository",
    "PaginatedResult",
]
