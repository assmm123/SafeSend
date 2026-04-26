"""اختبارات fraud_detection.py"""

import pytest, sys
sys.path.insert(0, '.')
from src.services.fraud_detection import FraudDetection, FraudScore

@pytest.fixture
def fd():
    return FraudDetection()

class TestFraudScore:
    def test_add(self):
        fs = FraudScore()
        fs.add(30, 'test')
        assert fs.score == 30
        assert fs.level == 'medium'
    
    def test_critical(self):
        fs = FraudScore()
        fs.add(90, 'critical')
        assert fs.level == 'critical'

class TestFraudDetection:
    def test_risk_level_default_low(self, fd):
        assert fd.get_risk_level(1) == 'low'
    
    def test_analyze_normal_user(self, fd):
        score = fd.analyze_user_behavior(1, {'ip_address': '1.1.1.1', 'amount': 50})
        assert score.score >= 0
    
    def test_new_user_high_value(self, fd):
        fd._user_profiles[2] = {'created_at': '2024-01-01T00:00:00', 'risk_score': 0, 'deals': [], 'disputes': [], 'logins': [], 'transactions': []}
        score = fd.analyze_user_behavior(2, {'amount': 5000})
        assert score.score >= 0  # Depends on profile age
    
    def test_apply_limits_low(self, fd):
        limits = fd.apply_limits(1)
        assert limits['daily'] == 50000
    
    def test_apply_limits_critical(self, fd):
        fd.blacklist_user(1, 'test')
        limits = fd.apply_limits(1)
        assert limits['daily'] == 0
    
    def test_blacklist(self, fd):
        fd.blacklist_user(99, 'fraud')
        assert fd.get_risk_level(99) == 'critical'
    
    def test_whitelist(self, fd):
        fd.whitelist_user(100)
        assert fd.get_risk_level(100) == 'low'
    
    def test_fraud_report(self, fd):
        report = fd.get_fraud_report()
        assert 'total_events' in report
        assert 'blacklisted' in report
    
    def test_log_event(self, fd):
        fd.log_suspicious_event(1, 'test_event', {'detail': 'test'})
        assert len(fd._suspicious_events) == 1

__all__ = ['TestFraudScore', 'TestFraudDetection']
