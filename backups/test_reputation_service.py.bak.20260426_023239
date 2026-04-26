"""اختبارات reputation_service.py"""

import pytest, sys
sys.path.insert(0, '.')
from src.services.reputation_service import ReputationService

@pytest.fixture
def rs():
    return ReputationService()

class TestAddReview:
    def test_add_review(self, rs):
        r = rs.add_review(1, 10, 20, {'communication':5,'quality':4,'speed':5,'accuracy':4}, 'Great!')
        assert r['success'] is True

class TestTrustScore:
    def test_calculate(self, rs):
        rs.set_user_stats(1, {'completed_deals':20, 'kyc_verified':True, 'two_factor_enabled':True, 'disputes':1})
        rs.add_review(1, 10, 1, {'com':5,'qua':5,'spd':5,'acc':5})
        score = rs.calculate_trust_score(1)
        assert 0 <= score <= 100
        assert score > 0

class TestBadges:
    def test_badges(self, rs):
        rs.set_user_stats(1, {'completed_deals':100, 'kyc_verified':True, 'two_factor_enabled':True, 'disputes':0})
        rs.add_review(1, 10, 1, {'c':5,'q':5,'s':5,'a':5})
        badges = rs.get_user_badges(1)
        assert len(badges) >= 1
        assert any('Expert' in b or 'Trusted' in b or 'Top Seller' in b for b in badges)

class TestPostDeal:
    def test_update(self, rs):
        r = rs.update_reputation_after_deal(1, 10, 20, 500)
        assert r['success'] is True

class TestBreakdown:
    def test_breakdown(self, rs):
        rs.add_review(1, 10, 1, {'c':4,'q':4,'s':4,'a':4})
        bd = rs.get_reputation_breakdown(1)
        assert 'trust_score' in bd
        assert 'badges' in bd

__all__ = ['TestAddReview', 'TestTrustScore', 'TestBadges', 'TestPostDeal', 'TestBreakdown']
