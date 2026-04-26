"""
Badge Model - SafeSend
نموذج الشارات - SafeSend

User achievement badges with auto-award, expiration, and progress tracking.
شارات إنجاز المستخدم مع منح تلقائي، صلاحية، وتتبع التقدم.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
import structlog

from src.app.models.base import BaseModel

logger = structlog.get_logger(__name__)

# Badge definitions
BADGE_DEFINITIONS = {
    'early_adopter': {
        'name': 'Early Adopter', 'name_ar': 'مبكر', 'icon': '🆕',
        'description': 'Among the first 1000 users / من أول 1000 مستخدم',
        'duration_days': None, 'requirements': {'max_user_id': 1000}
    },
    'trusted': {
        'name': 'Trusted', 'name_ar': 'موثوق', 'icon': '🤝',
        'description': '10+ deals with 4.0+ rating / 10+ صفقات بتقييم 4.0+',
        'duration_days': 365, 'requirements': {'min_deals': 10, 'min_rating': 4.0}
    },
    'top_rated': {
        'name': 'Top Rated', 'name_ar': 'الأعلى تقييماً', 'icon': '⭐',
        'description': '4.8+ rating with 50+ reviews / تقييم 4.8+ مع 50+ مراجعة',
        'duration_days': 180, 'requirements': {'min_reviews': 50, 'min_rating': 4.8}
    },
    'top_seller': {
        'name': 'Top Seller', 'name_ar': 'أفضل بائع', 'icon': '💰',
        'description': '100+ completed deals / 100+ صفقة مكتملة',
        'duration_days': 365, 'requirements': {'min_deals': 100}
    },
    'security_expert': {
        'name': 'Security Expert', 'name_ar': 'خبير أمني', 'icon': '🛡️',
        'description': '2FA enabled + KYC verified + 0 disputes / 2FA مفعل + KYC + 0 نزاعات',
        'duration_days': None, 'requirements': {'two_factor': True, 'kyc': True, 'max_disputes': 0}
    },
    'perfect_streak': {
        'name': 'Perfect Streak', 'name_ar': 'سلسلة مثالية', 'icon': '🎯',
        'description': '10 consecutive 5-star reviews / 10 تقييمات 5 نجوم متتالية',
        'duration_days': 90, 'requirements': {'consecutive_five_star': 10}
    },
    'deal_master': {
        'name': 'Deal Master', 'name_ar': 'سيد الصفقات', 'icon': '🏆',
        'description': '500+ completed deals / 500+ صفقة مكتملة',
        'duration_days': None, 'requirements': {'min_deals': 500}
    },
    'hot_streak': {
        'name': 'Hot Streak', 'name_ar': 'نشاط متواصل', 'icon': '🔥',
        'description': '10 deals in 30 days / 10 صفقات في 30 يوم',
        'duration_days': 30, 'requirements': {'min_deals_30_days': 10}
    },
    'elite': {
        'name': 'Elite', 'name_ar': 'نخبة', 'icon': '💎',
        'description': '200+ deals + 4.9+ rating / 200+ صفقة + تقييم 4.9+',
        'duration_days': None, 'requirements': {'min_deals': 200, 'min_rating': 4.9}
    }
}

class Badge(BaseModel):
    """
    User achievement badge.
    شارة إنجاز المستخدم.
    
    Awarded automatically when requirements are met.
    تمنح تلقائياً عند تحقيق المتطلبات.
    """
    __tablename__ = 'badges'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    badge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(10), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    awarded_by: Mapped[str] = mapped_column(String(20), default='system', nullable=False)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user = relationship('User', foreign_keys=[user_id])

    __table_args__ = (
        Index('ix_badges_user_id', 'user_id'),
        Index('ix_badges_badge_type', 'badge_type'),
        Index('ix_badges_is_active', 'is_active'),
        Index('ix_badges_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f"<Badge(user={self.user_id}, type={self.badge_type})>"

    # ============================================================
    # Award & Revoke
    # ============================================================

    @classmethod
    def award(cls, user_id: int, badge_type: str, duration_days: Optional[int] = None) -> 'Badge':
        """
        Award a badge to a user.
        منح شارة لمستخدم.
        """
        definition = BADGE_DEFINITIONS.get(badge_type)
        if not definition:
            raise ValueError(f"Unknown badge type: {badge_type}")
        
        duration = duration_days or definition.get('duration_days')
        
        badge = cls()
        badge.user_id = user_id
        badge.badge_type = badge_type
        badge.badge_name = definition['name']
        badge.badge_icon = definition['icon']
        badge.earned_at = datetime.now(timezone.utc)
        badge.expires_at = datetime.now(timezone.utc) + timedelta(days=duration) if duration else None
        badge.is_active = True
        badge.awarded_by = 'system'
        
        logger.info("badge.awarded", user_id=user_id, badge_type=badge_type)
        return badge

    def revoke(self, reason: str = 'requirements_lost') -> None:
        """
        Revoke a badge.
        سحب شارة.
        """
        self.is_active = False
        self.revoke_reason = reason
        logger.info("badge.revoked", badge_id=self.id, reason=reason)

    def renew(self) -> None:
        """Renew an expiring badge. / تجديد شارة."""
        definition = BADGE_DEFINITIONS.get(self.badge_type)
        if definition and definition.get('duration_days'):
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=definition['duration_days'])
            self.is_active = True
            logger.info("badge.renewed", badge_id=self.id)

    # ============================================================
    # Status Checks
    # ============================================================

    def is_expired(self) -> bool:
        """Check if badge has expired. / فحص انتهاء صلاحية الشارة."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def check_and_update_status(self) -> None:
        """Auto-revoke if expired. / سحب تلقائي عند الانتهاء."""
        if self.is_expired() and self.is_active:
            self.revoke('expired')

    # ============================================================
    # Eligibility
    # ============================================================

    @classmethod
    def check_eligibility(cls, badge_type: str, stats: Dict[str, Any]) -> bool:
        """
        Check if user meets badge requirements.
        فحص أهلية المستخدم للشارة.
        """
        definition = BADGE_DEFINITIONS.get(badge_type)
        if not definition:
            return False
        
        req = definition['requirements']
        
        if 'max_user_id' in req and stats.get('user_id', 9999) > req['max_user_id']:
            return False
        if 'min_deals' in req and stats.get('completed_deals', 0) < req['min_deals']:
            return False
        if 'min_deals_30_days' in req and stats.get('deals_30_days', 0) < req['min_deals_30_days']:
            return False
        if 'min_rating' in req and stats.get('rating', 0) < req['min_rating']:
            return False
        if 'min_reviews' in req and stats.get('total_reviews', 0) < req['min_reviews']:
            return False
        if 'two_factor' in req and not stats.get('two_factor_enabled', False):
            return False
        if 'kyc' in req and not stats.get('kyc_verified', False):
            return False
        if 'max_disputes' in req and stats.get('disputes', 0) > req['max_disputes']:
            return False
        if 'consecutive_five_star' in req and stats.get('consecutive_5star', 0) < req['consecutive_five_star']:
            return False
        
        return True

    @classmethod
    def get_progress(cls, badge_type: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get progress percentage toward badge.
        نسبة التقدم نحو الشارة.
        """
        definition = BADGE_DEFINITIONS.get(badge_type)
        if not definition:
            return {'eligible': False, 'progress': 0}
        
        req = definition['requirements']
        progress = {}
        total_pct = 0
        count = 0
        
        for key, target in req.items():
            current = stats.get(key, 0)
            if isinstance(target, bool):
                progress[key] = {'current': current, 'target': target, 'met': current == target}
                if current == target:
                    total_pct += 100
            else:
                pct = min(100, (current / target) * 100) if target > 0 else 100
                progress[key] = {'current': current, 'target': target, 'percent': round(pct, 1)}
                total_pct += pct
            count += 1
        
        return {
            'eligible': cls.check_eligibility(badge_type, stats),
            'overall_progress': round(total_pct / count, 1) if count > 0 else 0,
            'requirements': progress
        }

    # ============================================================
    # Queries
    # ============================================================

    @classmethod
    def get_user_badges(cls, session, user_id: int) -> List['Badge']:
        """Get all badges for a user. / جميع شارات المستخدم."""
        return session.query(cls).filter(cls.user_id == user_id).all()

    @classmethod
    def get_active_badges(cls, session, user_id: int) -> List['Badge']:
        """Get active (non-expired) badges. / الشارات النشطة."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_active == True
        ).all()

    # ============================================================
    # Serialization
    # ============================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary. / تحويل إلى قاموس."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'badge_type': self.badge_type,
            'badge_name': self.badge_name,
            'badge_icon': self.badge_icon,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired()
        }

    @classmethod
    def get_all_definitions(cls) -> List[Dict[str, Any]]:
        """Get all badge definitions. / جميع تعريفات الشارات."""
        return [
            {
                'type': key,
                'name': val['name'],
                'name_ar': val['name_ar'],
                'icon': val['icon'],
                'description': val['description'],
                'duration_days': val.get('duration_days'),
                'requirements': val['requirements']
            }
            for key, val in BADGE_DEFINITIONS.items()
        ]


__all__ = ['Badge', 'BADGE_DEFINITIONS']
