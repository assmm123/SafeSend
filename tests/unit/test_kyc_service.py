"""اختبارات kyc_service.py"""

import pytest, sys
sys.path.insert(0, '.')
from src.services.kyc_service import KYCService, VERIFICATION_LEVELS

@pytest.fixture
def kyc():
    return KYCService()

class TestTelegram:
    def test_valid(self, kyc):
        r = kyc.verify_telegram(1, 123456789); assert r['success']
    def test_invalid(self, kyc):
        r = kyc.verify_telegram(1, 0); assert not r['success']

class TestEmail:
    def test_valid(self, kyc):
        r = kyc.verify_email(1, 'test@example.com'); assert r['success']
    def test_invalid(self, kyc):
        r = kyc.verify_email(1, 'invalid'); assert not r['success']

class TestDocument:
    def test_valid(self, kyc):
        r = kyc.verify_document(1, 'passport', 'AB123456'); assert r['success']
    def test_invalid_type(self, kyc):
        r = kyc.verify_document(1, 'invalid', '123'); assert not r['success']
    def test_invalid_number(self, kyc):
        r = kyc.verify_document(1, 'passport', '12'); assert not r['success']

class TestGitHub:
    def test_valid(self, kyc):
        r = kyc.verify_github(1, 'testuser'); assert r['success']
    def test_invalid(self, kyc):
        r = kyc.verify_github(1, ''); assert not r['success']

class TestPhone:
    def test_valid(self, kyc):
        r = kyc.verify_phone(1, '0933333333'); assert r['success']
    def test_invalid(self, kyc):
        r = kyc.verify_phone(1, '123'); assert not r['success']

class TestTrustLevel:
    def test_default_zero(self, kyc):
        t = kyc.get_trust_level(1); assert t['level'] == 0
    def test_upgrade_with_verifications(self, kyc):
        kyc.verify_email(1, 't@t.com'); kyc.verify_phone(1, '0933333333')
        kyc.verify_telegram(1, 123); t = kyc.get_trust_level(1)
        assert t['level'] >= 1
    def test_daily_limit_increases(self, kyc):
        limits_before = kyc.get_transaction_limit(1)
        kyc.verify_email(1, 't@t.com'); kyc.verify_document(1, 'passport', 'AB123456')
        kyc.verify_selfie(1, 'selfie.jpg'); kyc.verify_address(1, '123 Main St, City, Country')
        limits_after = kyc.get_transaction_limit(1)
        assert limits_after['daily'] >= limits_before['daily']

class TestProgress:
    def test_progress(self, kyc):
        p = kyc.get_verification_progress(1); assert 'progress_pct' in p
    def test_progress_after_verify(self, kyc):
        kyc.verify_email(1, 't@t.com')
        p = kyc.get_verification_progress(1); assert p['progress_pct'] > 0

__all__ = ['TestTelegram', 'TestEmail', 'TestDocument', 'TestGitHub', 'TestPhone', 'TestTrustLevel', 'TestProgress']
