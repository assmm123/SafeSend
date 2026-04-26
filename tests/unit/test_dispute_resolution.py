"""اختبارات dispute_resolution.py"""

import pytest, sys
sys.path.insert(0, '.')
from src.services.dispute_resolution import DisputeResolution

@pytest.fixture
def dr():
    return DisputeResolution()

class TestCreate:
    def test_create_dispute(self, dr):
        r = dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        assert r['success'] is True
        assert r['dispute']['status'] == 'opened'

    def test_invalid_category(self, dr):
        r = dr.create_dispute(1, 10, 20, 'Bad', 'invalid')
        assert r['success'] is False

class TestEvidence:
    def test_add_evidence(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        r = dr.add_evidence(1, {'type': 'screenshot', 'url': 'http://img.com/1.jpg'}, 10)
        assert r['success'] is True

class TestMediator:
    def test_assign_auto(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        r = dr.assign_mediator(1)
        assert r['success'] is True
        assert r['mediator_id'] is not None

class TestResolve:
    def test_resolve_refund(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        r = dr.resolve_dispute(1, 999, 'refund_buyer', 'evidence clear')
        assert r['success'] is True
        d = dr.get_dispute(1)
        assert d['status'] == 'resolved_buyer'

    def test_cant_resolve_twice(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        dr.resolve_dispute(1, 999, 'refund_buyer')
        r = dr.resolve_dispute(1, 999, 'pay_seller')
        assert r['success'] is False

class TestAppeal:
    def test_appeal(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        dr.resolve_dispute(1, 999, 'refund_buyer')
        r = dr.appeal_decision(1, 10, 'unfair decision')
        assert r['success'] is True

    def test_max_appeals(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        dr.resolve_dispute(1, 999, 'refund_buyer')
        dr.appeal_decision(1, 10, 'first')
        r = dr.appeal_decision(1, 10, 'second')
        assert r['success'] is False

class TestQueries:
    def test_timeline(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        assert len(dr.get_dispute_timeline(1)) == 1

    def test_user_disputes(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        assert len(dr.get_user_disputes(10)) == 1

class TestEscalate:
    def test_escalate(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        r = dr.escalate_to_owner(1, 'urgent')
        assert r['success'] is True

class TestClose:
    def test_close(self, dr):
        dr.create_dispute(1, 10, 20, 'Bad quality', 'quality')
        r = dr.close_dispute(1, 999)
        assert r['success'] is True
        assert dr.get_dispute(1)['status'] == 'closed'

__all__ = ['TestCreate', 'TestEvidence', 'TestMediator', 'TestResolve', 'TestAppeal', 'TestQueries', 'TestEscalate', 'TestClose']
