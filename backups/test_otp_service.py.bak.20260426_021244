"""اختبارات otp_service.py"""

import pytest, time, sys
sys.path.insert(0, '.')
from src.services.otp_service import OTPService, MAX_ATTEMPTS

@pytest.fixture
def otp():
    return OTPService()

class TestOTP:
    def test_generate_otp(self, otp): assert len(otp.generate_otp()) == 6 and otp.generate_otp().isdigit()
    def test_totp_secret(self, otp): assert len(otp.generate_totp_secret()) > 0
    def test_backup_codes(self, otp): assert len(otp.generate_backup_codes()) == 8

class TestSend:
    def test_email(self, otp):
        r = otp.send_email_otp(1, 't@t.com'); assert r['success'] and len(r['otp']) == 6
    def test_telegram(self, otp):
        r = otp.send_telegram_otp(1, 123); assert r['success']
    def test_rate_limit(self, otp):
        otp.send_email_otp(1, 't@t.com'); assert otp.send_email_otp(1, 't@t.com')['error'] == 'rate_limited'

class TestVerify:
    def test_success(self, otp):
        r = otp.send_email_otp(1, 't@t.com'); assert otp.verify_otp(1, r['otp'])['success']
    def test_invalid(self, otp):
        otp.send_email_otp(1, 't@t.com'); assert not otp.verify_otp(1, '000000')['success']
    def test_no_otp(self, otp): assert otp.verify_otp(99, '123456')['error'] == 'no_otp'
    def test_block(self, otp):
        otp.send_email_otp(1, 't@t.com')
        for _ in range(MAX_ATTEMPTS): otp.verify_otp(1, '000000')
        assert otp.verify_otp(1, '000000')['error'] == 'blocked'

class TestTOTP:
    def test_verify_valid(self, otp):
        import pyotp
        s = otp.generate_totp_secret(); assert otp.verify_totp(s, pyotp.TOTP(s).now())
    def test_verify_invalid(self, otp):
        assert not otp.verify_totp(otp.generate_totp_secret(), '000000')

class TestCleanup:
    def test_revoke(self, otp): otp.send_email_otp(1, 't@t.com'); assert otp.revoke_all(1) == 1
    def test_expired(self, otp):
        otp.send_email_otp(1, 't@t.com'); otp._otp_store['email:1']['expires_at'] = time.time()-10
        assert otp.cleanup_expired() == 1
