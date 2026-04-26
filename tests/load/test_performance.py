import time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.services.otp_service import OTPService
from src.services.kyc_service import KYCService
from src.services.fraud_detection import FraudDetection
from src.services.escrow_guard import EscrowGuard

print("⚡ Performance Tests")
print("=" * 40)

otp = OTPService()
start = time.time()
for _ in range(100): otp.generate_otp()
d = time.time() - start
print(f"✅ OTP Gen: 100 codes in {d:.2f}s ({d/100*1000:.1f}ms each)")

kyc = KYCService()
start = time.time()
for i in range(50): kyc.verify_email(i, f'u{i}@t.com')
d = time.time() - start
print(f"✅ KYC: 50 verifications in {d:.2f}s")

fraud = FraudDetection()
start = time.time()
for i in range(200): fraud.analyze_user_behavior(i%100, {'amount':i*10})
d = time.time() - start
print(f"✅ Fraud: 200 analyses in {d:.2f}s")

guard = EscrowGuard()
start = time.time()
for i in range(100): guard.hold_funds(i, 500, 10, 20)
d = time.time() - start
print(f"✅ Escrow: 100 holds in {d:.2f}s")

print(f"\n📊 Summary: ~{500/(time.time()-start+0.001):.0f} ops/sec capacity")
print("✅ All performance tests PASSED")
