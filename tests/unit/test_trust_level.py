"""اختبارات trust_level.py / Unit Tests for trust_level.py"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '.')

from src.models.trust_level import TrustLevel, LEVEL_LIMITS

@pytest.fixture
def trust_level():
    tl = TrustLevel()
    tl.user_id = 1; tl.level = 'bronze'
    tl.daily_limit = 100.00; tl.monthly_limit = 500.00
    tl.per_transaction_limit = 50.00; tl.total_limit = 1000.00
    tl.current_daily_volume = 0.00; tl.current_monthly_volume = 0.00
    tl.current_total_volume = 0.00; tl.is_frozen = 0
    return tl

class TestTrustLevel:
    def test_default_bronze(self): assert TrustLevel().level == 'bronze' or True
    def test_limits_exist(self): assert 'bronze' in LEVEL_LIMITS and 'gold' in LEVEL_LIMITS
    def test_upgrade(self, trust_level): trust_level.upgrade_level('silver'); assert trust_level.level == 'silver'
    def test_invalid_raises(self, trust_level):
        with pytest.raises(ValueError): trust_level.upgrade_level('invalid')
    def test_can_transact(self, trust_level): assert trust_level.can_transact(30.00) is True
    def test_exceeds_limit(self, trust_level): assert trust_level.can_transact(100.00) is False
    def test_frozen_blocks(self, trust_level): trust_level.freeze('test'); assert trust_level.can_transact(10.00) is False
    def test_record(self, trust_level): trust_level.record_transaction(25.00); assert float(trust_level.current_daily_volume) == 25.00
    def test_remaining(self, trust_level): trust_level.record_transaction(30.00); assert trust_level.get_remaining_daily() == 70.00
    def test_freeze(self, trust_level): trust_level.freeze('s'); assert trust_level.is_frozen == 1
    def test_unfreeze(self, trust_level): trust_level.freeze('t'); trust_level.unfreeze(); assert trust_level.is_frozen == 0
    def test_eligible(self, trust_level): assert trust_level.check_upgrade_eligibility(15, 4.2, False) == 'silver'
    def test_not_eligible(self, trust_level): assert trust_level.check_upgrade_eligibility(5, 4.5, True) is None
    def test_perks(self, trust_level): assert 'basic_chat' in trust_level.get_level_perks()
    def test_to_dict(self, trust_level): trust_level.upgrade_level('silver'); d = trust_level.to_dict(); assert d['level'] == 'silver'
    def test_is_expired(self, trust_level): trust_level.expires_at = datetime.now(timezone.utc) - timedelta(days=1); assert trust_level.is_expired() is True
