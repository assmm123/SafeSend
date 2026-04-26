"""
Review Model - SafeSend
نموذج التقييمات - SafeSend

Complete review system with rewards, badges, verification, and anti-fraud protection.
نظام تقييمات متكامل مع مكافآت وشارات وتوثيق وحماية من التلاعب.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, JSON, ForeignKey, Boolean, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
import structlog

from src.app.models.base import BaseModel

logger = structlog.get_logger(__name__)

REWARD_DETAILED = 10
REWARD_QUICK = 2
REWARD_VIDEO = 20
REWARD_FIVE_STAR = 5
REWARD_VERIFIED_MULTIPLIER = 2
EDIT_WINDOW_HOURS = 48
DELETE_BLOCK_HOURS = 24

BADGE_TRUSTED = {'min_reviews': 10, 'min_rating': 4.0, 'name': 'Trusted Reviewer', 'icon': '🥉'}
BADGE_EXPERT = {'min_reviews': 50, 'min_rating': 4.5, 'name': 'Expert Reviewer', 'icon': '🥈'}
BADGE_VIP = {'min_reviews': 200, 'min_rating': 4.8, 'name': 'VIP Reviewer', 'icon': '🥇'}
BADGE_ELITE = {'min_reviews': 500, 'min_rating': 4.9, 'name': 'Elite Reviewer', 'icon': '💎'}

class Review(BaseModel):
    """User review and rating. / تقييم المستخدم."""
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reviewed_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    communication_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    speed_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)

    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=True)

    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified_reviewer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_badge: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    reviewer_reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reviewed_bonus_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Use string references to avoid circular imports
    deal = relationship('Deal', foreign_keys=[deal_id])
    reviewer = relationship('User', foreign_keys=[reviewer_id])
    reviewed = relationship('User', foreign_keys=[reviewed_id])

    __table_args__ = (
        UniqueConstraint('deal_id', 'reviewer_id', name='uq_deal_reviewer'),
        Index('ix_reviews_deal_id', 'deal_id'),
        Index('ix_reviews_reviewer_id', 'reviewer_id'),
        Index('ix_reviews_reviewed_id', 'reviewed_id'),
        Index('ix_reviews_overall_rating', 'overall_rating'),
        Index('ix_reviews_is_flagged', 'is_flagged'),
    )

    def calculate_overall(self) -> float:
        self.overall_rating = round((self.communication_rating + self.quality_rating + self.speed_rating + self.accuracy_rating) / 4, 2)
        return self.overall_rating

    def verify_purchase(self) -> None:
        self.is_verified_purchase = True

    def verify_reviewer(self, badge: str = 'trusted') -> None:
        self.is_verified_reviewer = True
        self.verification_badge = badge

    def flag_suspicious(self, reason: str) -> None:
        self.is_flagged = True
        self.flag_reason = reason

    def calculate_reward(self, review_type: str = 'detailed') -> int:
        rewards = {'detailed': REWARD_DETAILED, 'quick': REWARD_QUICK, 'video': REWARD_VIDEO}
        base = rewards.get(review_type, REWARD_QUICK)
        if self.overall_rating and self.overall_rating >= 5.0:
            base += REWARD_FIVE_STAR
        if self.is_verified_reviewer:
            base *= REWARD_VERIFIED_MULTIPLIER
        self.reviewer_reward_points = base
        self.reward_type = review_type
        return base

    def award_reviewed_bonus(self) -> int:
        if self.overall_rating and self.overall_rating >= 5.0:
            self.reviewed_bonus_points = REWARD_FIVE_STAR
            return REWARD_FIVE_STAR
        return 0

    @staticmethod
    def get_reviewer_badge(total_reviews: int, avg_rating: float) -> Optional[Dict[str, Any]]:
        for badge in [BADGE_ELITE, BADGE_VIP, BADGE_EXPERT, BADGE_TRUSTED]:
            if total_reviews >= badge['min_reviews'] and avg_rating >= badge['min_rating']:
                return badge
        return None

    def hide(self, reason: str = '') -> None:
        self.is_hidden = True
        self.admin_notes = reason

    def unhide(self) -> None:
        self.is_hidden = False

    def edit_comment(self, new_comment: str) -> bool:
        if not self.created_at:
            return False
        if datetime.now(timezone.utc) > self.created_at + timedelta(hours=EDIT_WINDOW_HOURS):
            return False
        self.comment = new_comment
        self.edited_at = datetime.now(timezone.utc)
        return True

    def can_delete(self) -> bool:
        if not self.created_at:
            return True
        return datetime.now(timezone.utc) <= self.created_at + timedelta(hours=DELETE_BLOCK_HOURS)

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data = {
            'id': self.id, 'deal_id': self.deal_id,
            'reviewer_id': self.reviewer_id if include_sensitive else None,
            'reviewed_id': self.reviewed_id,
            'ratings': {'communication': self.communication_rating, 'quality': self.quality_rating,
                        'speed': self.speed_rating, 'accuracy': self.accuracy_rating,
                        'overall': float(self.overall_rating) if self.overall_rating else None},
            'comment': self.comment if not self.is_hidden else None,
            'tags': self.tags or [],
            'is_verified_purchase': self.is_verified_purchase,
            'verification_badge': self.verification_badge,
            'reward_points': self.reviewer_reward_points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        return data

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'ratings': {'communication': self.communication_rating, 'quality': self.quality_rating,
                        'speed': self.speed_rating, 'accuracy': self.accuracy_rating,
                        'overall': float(self.overall_rating) if self.overall_rating else None},
            'comment': self.comment if not self.is_hidden else '[مخفي]',
            'tags': self.tags or [],
            'is_verified_purchase': self.is_verified_purchase,
            'verification_badge': self.verification_badge,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


__all__ = ['Review', 'BADGE_TRUSTED', 'BADGE_EXPERT', 'BADGE_VIP', 'BADGE_ELITE']
