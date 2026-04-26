"""اختبارات badge.py"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '.')

from src.models.badge import Badge, BADGE_DEFINITIONS

@pytest.fixture
def badge():
    b = Badge()
    b.id = 1; b.user_id = 100
    b.badge_type = 'trusted'; b.badge_name = 'Trusted'
    b.badge_icon = '🤝'; b.is_active = True
    b.earned_at = datetime.now(timezone.utc)
    return b

class TestBadge:
    def test_award(self):
        b = Badge.award(100, 'trusted')
        assert b.badge_type == 'trusted'
        assert b.is_active is True
    
    def test_award_invalid(self):
        with pytest.raises(ValueError):
            Badge.award(100, 'nonexistent')
    
    def test_award_permanent(self):
        b = Badge.award(100, 'early_adopter')
        assert b.expires_at is None
    
    def test_award_temporary(self):
        b = Badge.award(100, 'hot_streak')
        assert b.expires_at is not None
    
    def test_revoke(self, badge):
        badge.revoke('lost_requirements')
        assert badge.is_active is False
        assert badge.revoke_reason == 'lost_requirements'
    
    def test_renew(self, badge):
        badge.badge_type = 'trusted'
        badge.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        badge.renew()
        assert badge.is_active is True
        assert badge.expires_at > datetime.now(timezone.utc)
    
    def test_is_expired_false(self, badge):
        badge.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        assert badge.is_expired() is False
    
    def test_is_expired_true(self, badge):
        badge.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert badge.is_expired() is True
    
    def test_is_expired_permanent(self, badge):
        badge.expires_at = None
        assert badge.is_expired() is False
    
    def test_auto_revoke_expired(self, badge):
        badge.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        badge.is_active = True
        badge.check_and_update_status()
        assert badge.is_active is False
    
    def test_check_eligibility_trusted(self):
        stats = {'completed_deals': 15, 'rating': 4.2}
        assert Badge.check_eligibility('trusted', stats) is True
    
    def test_check_eligibility_not_met(self):
        stats = {'completed_deals': 3, 'rating': 3.5}
        assert Badge.check_eligibility('trusted', stats) is False
    
    def test_check_eligibility_security(self):
        stats = {'two_factor_enabled': True, 'kyc_verified': True, 'disputes': 0}
        assert Badge.check_eligibility('security_expert', stats) is True
    
    def test_get_progress(self):
        stats = {'completed_deals': 5, 'rating': 3.8}
        progress = Badge.get_progress('trusted', stats)
        assert 'overall_progress' in progress
        assert progress['eligible'] is False  # 5 < 10 deals
    
    def test_to_dict(self, badge):
        d = badge.to_dict()
        assert d['badge_type'] == 'trusted'
        assert d['is_active'] is True
    
    def test_get_all_definitions(self):
        defs = Badge.get_all_definitions()
        assert len(defs) >= 9
        assert any(d['type'] == 'elite' for d in defs)

__all__ = ['TestBadge']
