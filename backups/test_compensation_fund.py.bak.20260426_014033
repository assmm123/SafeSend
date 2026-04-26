"""اختبارات compensation_fund.py"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '.')

from src.models.compensation_fund import CompensationFund, FUND_HOLD_HOURS

@pytest.fixture
def fund():
    cf = CompensationFund()
    cf.id = 1
    cf.transaction_id = 100
    cf.amount = 5.00
    cf.status = 'collected'
    return cf

class TestCompensationFund:
    def test_collect(self, fund):
        fund.collect(5.00)
        assert fund.status == 'held'
        assert fund.hold_until is not None
    
    def test_release_held(self, fund):
        fund.status = 'held'
        fund.hold_until = datetime.now(timezone.utc) - timedelta(hours=FUND_HOLD_HOURS + 1)
        assert fund.release_held() is True
        assert fund.status == 'collected'
    
    def test_release_too_early(self, fund):
        fund.status = 'held'
        fund.hold_until = datetime.now(timezone.utc) + timedelta(hours=1)
        assert fund.release_held() is False
    
    def test_use_for_dispute(self, fund):
        assert fund.use_for_dispute(10, 2.00, 999) is True
        assert fund.status == 'used'
    
    def test_use_exceeds_max(self, fund):
        assert fund.use_for_dispute(10, 5.00, 999) is False
    
    def test_refund(self, fund):
        assert fund.refund_to_user(5.00) is True
        assert fund.status == 'refunded'
    
    def test_refund_wrong_status(self, fund):
        fund.status = 'used'
        assert fund.refund_to_user(5.00) is False
    
    def test_to_dict(self, fund):
        d = fund.to_dict()
        assert d['amount'] == 5.00
        assert d['status'] == 'collected'

__all__ = ['TestCompensationFund']
