"""اختبارات escrow_guard.py"""

import pytest, sys
sys.path.insert(0, '.')
from src.services.escrow_guard import EscrowGuard

@pytest.fixture
def guard():
    return EscrowGuard()

class TestHold:
    def test_hold_funds(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        assert h['status'] == 'held'
        assert h['amount'] == 500
    
    def test_hold_creates_history(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        assert len(h['history']) == 1

class TestRelease:
    def test_release_too_early(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        r = guard.release_funds(h['hold_id'], 10)
        assert r['success'] is False  # Too early
    
    def test_instant_release_request(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        r = guard.request_instant_release(h['hold_id'], 20, 'urgent')
        assert r['success'] is True
        assert r['requires_owner_approval'] is True
    
    def test_owner_approve_instant(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        guard.request_instant_release(h['hold_id'], 20, 'urgent')
        r = guard.owner_approve_release(h['hold_id'], 999, 'approved')
        assert r['success'] is True
        assert guard.get_hold_status(h['hold_id'])['status'] == 'released'
    
    def test_owner_reject_instant(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        guard.request_instant_release(h['hold_id'], 20, 'urgent')
        r = guard.owner_reject_release(h['hold_id'], 999, 'not now')
        assert r['success'] is True
    
    def test_small_amount_auto_approves(self, guard):
        h = guard.hold_funds(1, 50, 10, 20)  # Under $100
        r = guard.request_instant_release(h['hold_id'], 20, 'urgent')
        assert r['success'] is True

class TestDispute:
    def test_freeze_for_dispute(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        r = guard.freeze_for_dispute(h['hold_id'], 99)
        assert r['success'] is True
        assert guard.get_hold_status(h['hold_id'])['status'] == 'disputed'

class TestStatus:
    def test_get_status(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        s = guard.get_hold_status(h['hold_id'])
        assert s['status'] == 'held'
        assert 'remaining_hours' in s
    
    def test_pending_requests(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        guard.request_instant_release(h['hold_id'], 20, 'urgent')
        pending = guard.get_pending_instant_requests()
        assert len(pending) == 1
    
    def test_hold_history(self, guard):
        h = guard.hold_funds(1, 500, 10, 20)
        hist = guard.get_hold_history(h['hold_id'])
        assert len(hist) == 1

__all__ = ['TestHold', 'TestRelease', 'TestDispute', 'TestStatus']
