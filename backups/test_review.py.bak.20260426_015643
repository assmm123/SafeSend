"""اختبارات review.py"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '.')

from src.models.review import Review, BADGE_TRUSTED, BADGE_VIP

@pytest.fixture
def review():
    r = Review()
    r.id = 1; r.deal_id = 10; r.reviewer_id = 100; r.reviewed_id = 200
    r.communication_rating = 5; r.quality_rating = 4
    r.speed_rating = 5; r.accuracy_rating = 4
    r.created_at = datetime.now(timezone.utc)
    return r

class TestReview:
    def test_calculate_overall(self, review):
        overall = review.calculate_overall()
        assert overall == 4.5
    
    def test_verify_purchase(self, review):
        review.verify_purchase()
        assert review.is_verified_purchase is True
    
    def test_verify_reviewer(self, review):
        review.verify_reviewer('trusted')
        assert review.is_verified_reviewer is True
        assert review.verification_badge == 'trusted'
    
    def test_flag_suspicious(self, review):
        review.flag_suspicious('duplicate_pattern')
        assert review.is_flagged is True
    
    def test_calculate_reward_detailed(self, review):
        review.calculate_overall()
        points = review.calculate_reward('detailed')
        assert points == 10
    
    def test_calculate_reward_five_star(self, review):
        review.communication_rating = 5; review.quality_rating = 5
        review.speed_rating = 5; review.accuracy_rating = 5
        review.calculate_overall()
        points = review.calculate_reward('detailed')
        assert points == 15  # 10 + 5
    
    def test_calculate_reward_video(self, review):
        points = review.calculate_reward('video')
        assert points == 20
    
    def test_award_bonus_5star(self, review):
        review.overall_rating = 5.0
        bonus = review.award_reviewed_bonus()
        assert bonus == 5
    
    def test_award_bonus_not_5star(self, review):
        review.overall_rating = 4.0
        bonus = review.award_reviewed_bonus()
        assert bonus == 0
    
    def test_get_badge_trusted(self):
        badge = Review.get_reviewer_badge(15, 4.2)
        assert badge is not None
        assert 'Trusted' in badge['name']
    
    def test_get_badge_vip(self):
        badge = Review.get_reviewer_badge(250, 4.9)
        assert badge is not None
        assert 'VIP' in badge['name']
    
    def test_get_badge_none(self):
        badge = Review.get_reviewer_badge(3, 3.0)
        assert badge is None
    
    def test_hide_unhide(self, review):
        review.hide('inappropriate')
        assert review.is_hidden is True
        review.unhide()
        assert review.is_hidden is False
    
    def test_edit_comment(self, review):
        assert review.edit_comment('Updated!') is True
        assert review.edited_at is not None
    
    def test_edit_too_late(self, review):
        review.created_at = datetime.now(timezone.utc) - timedelta(hours=50)
        assert review.edit_comment('Too late') is False
    
    def test_can_delete(self, review):
        review.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
        assert review.can_delete() is True
    
    def test_cannot_delete(self, review):
        review.created_at = datetime.now(timezone.utc) - timedelta(hours=30)
        assert review.can_delete() is False
    
    def test_to_dict(self, review):
        d = review.to_dict()
        assert d['deal_id'] == 10
        assert 'ratings' in d
    
    def test_to_public_dict(self, review):
        d = review.to_public_dict()
        assert d['verification_badge'] is None
        assert 'reviewer_id' not in d  # Sensitive data excluded

__all__ = ['TestReview']
