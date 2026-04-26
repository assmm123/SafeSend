import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.services.otp_service import OTPService
from src.services.fraud_detection import FraudDetection
from src.services.escrow_guard import EscrowGuard

print("🛡️ Security Tests")
print("=" * 40)

otp = OTPService()
otp.send_email_otp(1, 't@t.com')
r = otp.send_email_otp(1, 't@t.com')
assert r['error'] == 'rate_limited'
print("✅ Rate Limiting: PASSED")

otp2 = OTPService()
otp2.send_email_otp(2, 't2@t.com')
for _ in range(3): otp2.verify_otp(2, '000000')
r = otp2.verify_otp(2, '000000')
assert r['error'] == 'blocked'
print("✅ Max Attempts Block: PASSED")

fraud = FraudDetection()
fraud.blacklist_user(99, 'test')
assert fraud.apply_limits(99)['daily'] == 0
print("✅ Blacklist Blocks All: PASSED")

guard = EscrowGuard()
h = guard.hold_funds(1, 500, 10, 20)
guard.owner_approve_release(h['hold_id'], 999)
r = guard.release_funds(h['hold_id'], 10)
assert r['success'] is False
print("✅ No Double Release: PASSED")

print("\n✅ All security tests PASSED")
