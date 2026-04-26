"""
Trust Level Model - SafeSend
نموذج مستوى الثقة - SafeSend
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Numeric, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
import structlog

from src.app.models.base import BaseModel

logger = structlog.get_logger(__name__)

LEVEL_LIMITS = {
    'bronze': {'daily':100.00,'monthly':500.00,'per_transaction':50.00,'total':1000.00,'perks':['basic_chat','standard_support'],'requirements':{'min_deals':0,'min_rating':0.0,'kyc_required':False}},
    'silver': {'daily':500.00,'monthly':2500.00,'per_transaction':250.00,'total':5000.00,'perks':['priority_chat','faster_payouts','standard_support'],'requirements':{'min_deals':10,'min_rating':4.0,'kyc_required':False}},
    'gold': {'daily':2000.00,'monthly':10000.00,'per_transaction':1000.00,'total':25000.00,'perks':['vip_chat','instant_payouts','priority_support','lower_fees'],'requirements':{'min_deals':50,'min_rating':4.5,'kyc_required':True}},
    'platinum': {'daily':10000.00,'monthly':50000.00,'per_transaction':5000.00,'total':100000.00,'perks':['vip_chat','instant_payouts','dedicated_support','lowest_fees','early_access'],'requirements':{'min_deals':200,'min_rating':4.8,'kyc_required':True}}
}

class TrustLevel(BaseModel):
    """User trust level and financial limits. / مستوى ثقة المستخدم وحدوده المالية."""
    __tablename__ = 'trust_levels'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default='bronze', nullable=False)
    daily_limit: Mapped[float] = mapped_column(Numeric(10,2), default=100.00, nullable=False)
    monthly_limit: Mapped[float] = mapped_column(Numeric(10,2), default=500.00, nullable=False)
    per_transaction_limit: Mapped[float] = mapped_column(Numeric(10,2), default=50.00, nullable=False)
    total_limit: Mapped[float] = mapped_column(Numeric(10,2), default=1000.00, nullable=False)
    current_daily_volume: Mapped[float] = mapped_column(Numeric(10,2), default=0.00, nullable=False)
    current_monthly_volume: Mapped[float] = mapped_column(Numeric(10,2), default=0.00, nullable=False)
    current_total_volume: Mapped[float] = mapped_column(Numeric(10,2), default=0.00, nullable=False)
    requirements_met = Column(JSON, default=dict, nullable=True)
    upgrade_history = Column(JSON, default=list, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_frozen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freeze_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    user = relationship('User', foreign_keys=[user_id])
    
    __table_args__ = (
        Index('ix_trust_levels_user_id', 'user_id'),
        Index('ix_trust_levels_level', 'level'),
        Index('ix_trust_levels_is_frozen', 'is_frozen'),
        Index('ix_trust_levels_expires_at', 'expires_at'),
    )

    def upgrade_level(self, new_level: str, reason: str = 'requirements_met') -> None:
        valid_levels = list(LEVEL_LIMITS.keys())
        if new_level not in valid_levels:
            raise ValueError(f"Invalid level: {new_level}")
        old_level = self.level
        limits = LEVEL_LIMITS[new_level]
        self.level = new_level
        self.daily_limit = limits['daily']
        self.monthly_limit = limits['monthly']
        self.per_transaction_limit = limits['per_transaction']
        self.total_limit = limits['total']
        self.verified_at = datetime.now(timezone.utc)
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        history = self.upgrade_history or []
        history.append({'from':old_level,'to':new_level,'reason':reason,'timestamp':datetime.now(timezone.utc).isoformat()})
        self.upgrade_history = history

    def downgrade_level(self, reason: str) -> None:
        levels = list(LEVEL_LIMITS.keys())
        idx = levels.index(self.level)
        if idx > 0:
            self.upgrade_level(levels[idx-1], f'downgraded: {reason}')

    def is_expired(self) -> bool:
        return bool(self.expires_at and datetime.now(timezone.utc) > self.expires_at)

    def renew(self, days: int = 365) -> None:
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        self.verified_at = datetime.now(timezone.utc)

    def get_limits(self) -> Dict[str, Any]:
        return {'level':self.level,'daily_limit':float(self.daily_limit),'monthly_limit':float(self.monthly_limit),'per_transaction_limit':float(self.per_transaction_limit),'remaining_daily':self.get_remaining_daily(),'remaining_monthly':self.get_remaining_monthly(),'is_frozen':bool(self.is_frozen)}

    def can_transact(self, amount: float) -> bool:
        if self.is_frozen or self.is_expired(): return False
        if amount > float(self.per_transaction_limit): return False
        if float(self.current_daily_volume)+amount > float(self.daily_limit): return False
        if float(self.current_monthly_volume)+amount > float(self.monthly_limit): return False
        return True

    def record_transaction(self, amount: float) -> None:
        self.current_daily_volume = float(self.current_daily_volume)+amount
        self.current_monthly_volume = float(self.current_monthly_volume)+amount
        self.current_total_volume = float(self.current_total_volume)+amount

    def reset_daily_volume(self) -> None: self.current_daily_volume = 0.00
    def reset_monthly_volume(self) -> None: self.current_monthly_volume = 0.00

    def get_remaining_daily(self) -> float:
        return max(0, float(self.daily_limit)-float(self.current_daily_volume))
    def get_remaining_monthly(self) -> float:
        return max(0, float(self.monthly_limit)-float(self.current_monthly_volume))

    def freeze(self, reason: str = 'suspicious_activity') -> None:
        self.is_frozen = 1; self.freeze_reason = reason
    def unfreeze(self) -> None:
        self.is_frozen = 0; self.freeze_reason = None

    def check_upgrade_eligibility(self, completed_deals: int, rating: float, kyc_verified: bool) -> Optional[str]:
        levels = list(LEVEL_LIMITS.keys())
        idx = levels.index(self.level)
        if idx >= len(levels)-1: return None
        next_level = levels[idx+1]
        req = LEVEL_LIMITS[next_level]['requirements']
        if completed_deals>=req['min_deals'] and rating>=req['min_rating'] and (not req['kyc_required'] or kyc_verified):
            return next_level
        return None

    def get_level_perks(self) -> list:
        return LEVEL_LIMITS.get(self.level,{}).get('perks',[])

    def to_dict(self) -> Dict[str, Any]:
        return {'id':self.id,'user_id':self.user_id,'level':self.level,'limits':{'daily':float(self.daily_limit),'monthly':float(self.monthly_limit),'per_transaction':float(self.per_transaction_limit)},'remaining':{'daily':self.get_remaining_daily(),'monthly':self.get_remaining_monthly()},'is_frozen':bool(self.is_frozen),'perks':self.get_level_perks(),'upgrade_history':self.upgrade_history}

__all__ = ['TrustLevel', 'LEVEL_LIMITS']
