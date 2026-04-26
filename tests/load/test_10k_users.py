"""
اختبار تحمل 10,000 مستخدم - SafeSend
10K Users Load Test - SafeSend
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.otp_service import OTPService
from src.services.kyc_service import KYCService
from src.services.fraud_detection import FraudDetection
from src.services.escrow_guard import EscrowGuard
from src.services.dispute_resolution import DisputeResolution
from src.services.reputation_service import ReputationService

print("=" * 60)
print("📊 SAFESEND - 10,000 USERS LOAD TEST")
print("=" * 60)

total_start = time.time()
total_operations = 0
errors = 0
warnings = 0

# Initialize all services
otp = OTPService()
kyc = KYCService()
fraud = FraudDetection()
guard = EscrowGuard()
dr = DisputeResolution()
rs = ReputationService()

print("\n👥 Simulating 10,000 users...")
print("=" * 60)

# Phase 1: Registration (10,000 users)
print("\n📝 Phase 1: User Registration (10,000 users)")
start = time.time()
for i in range(10000):
    try:
        otp.send_email_otp(i, f'user{i}@safesend.com')
        total_operations += 1
    except Exception as e:
        errors += 1
phase1_time = time.time() - start
print(f"   ⏱️ Time: {phase1_time:.2f}s")
print(f"   ⚡ Speed: {10000/phase1_time:.0f} users/sec")

# Phase 2: KYC Verification (10,000 users)
print("\n🛡️ Phase 2: KYC Verification (10,000 users)")
start = time.time()
for i in range(10000):
    try:
        kyc.verify_email(i, f'user{i}@safesend.com')
        kyc.verify_phone(i, f'09{i:08d}')
        total_operations += 2
    except Exception as e:
        errors += 1
phase2_time = time.time() - start
print(f"   ⏱️ Time: {phase2_time:.2f}s")
print(f"   ⚡ Speed: {20000/phase2_time:.0f} verifications/sec")

# Phase 3: Fraud Analysis (10,000 users)
print("\n🔍 Phase 3: Fraud Analysis (10,000 users)")
start = time.time()
for i in range(10000):
    try:
        fraud.analyze_user_behavior(i, {
            'ip_address': f'192.168.{i%255}.{i%100}',
            'amount': (i % 10 + 1) * 100
        })
        total_operations += 1
    except Exception as e:
        errors += 1
phase3_time = time.time() - start
print(f"   ⏱️ Time: {phase3_time:.2f}s")
print(f"   ⚡ Speed: {10000/phase3_time:.0f} analyses/sec")

# Phase 4: Escrow Holds (5,000 deals)
print("\n🔒 Phase 4: Escrow Holds (5,000 deals)")
start = time.time()
for i in range(5000):
    try:
        guard.hold_funds(i, (i % 100 + 1) * 10, buyer_id=i, seller_id=i+10000)
        total_operations += 1
    except Exception as e:
        errors += 1
phase4_time = time.time() - start
print(f"   ⏱️ Time: {phase4_time:.2f}s")
print(f"   ⚡ Speed: {5000/phase4_time:.0f} holds/sec")

# Phase 5: Disputes (1,000 disputes)
print("\n⚠️ Phase 5: Dispute Resolution (1,000 disputes)")
start = time.time()
for i in range(1000):
    try:
        result = dr.create_dispute(i, opened_by=i, against=i+1, 
                                   reason=f'Issue #{i}', category='quality')
        if result['success']:
            dispute_id = result['dispute']['id']
            dr.add_evidence(dispute_id, {'type':'log','data':f'evidence_{i}'}, i)
            dr.assign_mediator(dispute_id)
            dr.resolve_dispute(dispute_id, 999, 'refund_buyer', f'resolution_{i}')
        total_operations += 4
    except Exception as e:
        errors += 1
phase5_time = time.time() - start
print(f"   ⏱️ Time: {phase5_time:.2f}s")
print(f"   ⚡ Speed: {4000/phase5_time:.0f} operations/sec")

# Phase 6: Reviews & Reputation (5,000 reviews)
print("\n⭐ Phase 6: Reviews & Reputation (5,000 reviews)")
start = time.time()
for i in range(5000):
    try:
        ratings = {
            'communication': (i % 5) + 1,
            'quality': ((i+1) % 5) + 1,
            'speed': ((i+2) % 5) + 1,
            'accuracy': ((i+3) % 5) + 1
        }
        rs.add_review(i, reviewer_id=i, reviewed_id=i+100, ratings=ratings)
        if i % 10 == 0:
            rs.calculate_trust_score(i)
            total_operations += 1
        total_operations += 1
    except Exception as e:
        errors += 1
phase6_time = time.time() - start
print(f"   ⏱️ Time: {phase6_time:.2f}s")
print(f"   ⚡ Speed: {5500/phase6_time:.0f} operations/sec")

# Final Report
total_time = time.time() - total_start

print("\n" + "=" * 60)
print("📊 FINAL LOAD TEST REPORT")
print("=" * 60)
print(f"👥 Total Users Simulated: 10,000")
print(f"⚡ Total Operations: {total_operations:,}")
print(f"⏱️ Total Time: {total_time:.2f}s")
print(f"🚀 Overall Speed: {total_operations/total_time:.0f} ops/sec")
print(f"❌ Errors: {errors}")
print(f"📈 Capacity: {10000/total_time:.0f} users/sec")

# Rating
if total_time < 30 and errors == 0:
    rating = "🏆 EXCELLENT"
elif total_time < 60 and errors < 10:
    rating = "✅ GOOD"
elif total_time < 120 and errors < 50:
    rating = "⚠️ ACCEPTABLE"
else:
    rating = "❌ NEEDS IMPROVEMENT"

print(f"🏆 Performance Rating: {rating}")

# Memory estimate
import os as _os
mem_info = _os.popen('free -h 2>/dev/null || echo "N/A"').read().strip()
if mem_info != "N/A":
    print(f"\n💾 Memory Status:\n{mem_info}")

print("\n✅ 10K Load Test Complete!")
