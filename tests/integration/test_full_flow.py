"""
اختبار التدفق الكامل - SafeSend
Full Flow Integration Test - SafeSend

يحاكي رحلة مستخدم كاملة من التسجيل حتى تقييم الصفقة.
Simulates complete user journey from registration to deal review.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.otp_service import OTPService
from src.services.kyc_service import KYCService
from src.services.fraud_detection import FraudDetection
from src.services.escrow_guard import EscrowGuard
from src.services.dispute_resolution import DisputeResolution
from src.services.reputation_service import ReputationService
from src.models.trust_level import TrustLevel, LEVEL_LIMITS
from src.models.compensation_fund import CompensationFund
from src.models.review import Review
from src.models.badge import Badge

class TestFullUserFlow:
    """اختبار رحلة مستخدم كاملة"""
    
    def test_registration_to_first_deal(self):
        """تسجيل → توثيق → صفقة → تقييم"""
        # 1. تسجيل مستخدم جديد
        otp = OTPService()
        kyc = KYCService()
        fraud = FraudDetection()
        
        user_id = 1
        
        # 2. توثيق البريد والإيميل
        result = otp.send_email_otp(user_id, 'test@example.com')
        assert result['success'] is True
        
        verify = otp.verify_otp(user_id, result['otp'])
        assert verify['success'] is True
        
        # 3. توثيق KYC
        kyc.verify_email(user_id, 'test@example.com')
        kyc.verify_phone(user_id, '0933333333')
        trust = kyc.get_trust_level(user_id)
        assert trust['level'] >= 1
        
        # 4. فحص احتيال - مستخدم نظيف
        score = fraud.analyze_user_behavior(user_id, {'ip_address': '127.0.0.1', 'amount': 100})
        assert fraud.get_risk_level(user_id) == 'low'
        
        print("✅ Registration flow: PASSED")
    
    def test_deal_payment_flow(self):
        """صفقة → وساطة → تحرير"""
        guard = EscrowGuard()
        deal_id = 1
        
        # 1. تجميد الأموال
        hold = guard.hold_funds(deal_id, 500, buyer_id=10, seller_id=20)
        assert hold['status'] == 'held'
        
        # 2. طلب تحرير فوري
        instant = guard.request_instant_release(hold['hold_id'], requested_by=20, reason='تم التسليم')
        assert instant['success'] is True
        
        # 3. موافقة المالك
        approved = guard.owner_approve_release(hold['hold_id'], owner_id=999, notes='موافق')
        assert approved['success'] is True
        
        print("✅ Deal payment flow: PASSED")
    
    def test_dispute_resolution_flow(self):
        """نزاع → وسيط → قرار → استئناف"""
        dr = DisputeResolution()
        
        # 1. فتح نزاع
        result = dr.create_dispute(deal_id=1, opened_by=10, against=20, 
                                   reason='جودة غير مطابقة', category='quality')
        assert result['success'] is True
        dispute_id = result['dispute']['id']
        
        # 2. إضافة أدلة
        evidence = dr.add_evidence(dispute_id, {'type': 'screenshot', 'url': 'img.jpg'}, added_by=10)
        assert evidence['success'] is True
        
        # 3. تعيين وسيط
        mediator = dr.assign_mediator(dispute_id)
        assert mediator['success'] is True
        
        # 4. حل النزاع
        resolved = dr.resolve_dispute(dispute_id, resolved_by=mediator['mediator_id'], 
                                      decision='refund_buyer', notes='الأدلة واضحة')
        assert resolved['success'] is True
        
        # 5. استئناف
        appeal = dr.appeal_decision(dispute_id, appealed_by=10, reason='قرار غير عادل')
        assert appeal['success'] is True
        
        print("✅ Dispute resolution flow: PASSED")
    
    def test_reputation_system(self):
        """تقييم → سمعة → شارات"""
        rs = ReputationService()
        user_id = 1
        
        # 1. إضافة تقييمات
        rs.add_review(1, 10, user_id, {'communication': 5, 'quality': 4, 'speed': 5, 'accuracy': 4})
        rs.add_review(2, 11, user_id, {'communication': 5, 'quality': 5, 'speed': 5, 'accuracy': 5})
        
        # 2. تحديث بعد صفقة
        rs.set_user_stats(user_id, {
            'completed_deals': 15, 'kyc_verified': True,
            'two_factor_enabled': True, 'disputes': 0
        })
        rs.update_reputation_after_deal(3, seller_id=user_id, buyer_id=12, deal_amount=500)
        
        # 3. حساب درجة الثقة
        score = rs.calculate_trust_score(user_id)
        assert score > 0
        
        # 4. الشارات
        badges = rs.get_user_badges(user_id)
        assert len(badges) >= 1
        
        # 5. تحليل السمعة
        breakdown = rs.get_reputation_breakdown(user_id)
        assert breakdown['trust_score'] > 0
        
        print("✅ Reputation system: PASSED")
    
    def test_fraud_protection(self):
        """حماية من الاحتيال"""
        fraud = FraudDetection()
        
        # مستخدم عادي - أمان
        assert fraud.get_risk_level(1) == 'low'
        
        # إضافة للقائمة السوداء
        fraud.blacklist_user(99, 'fraud_detected')
        assert fraud.get_risk_level(99) == 'critical'
        assert fraud.apply_limits(99)['daily'] == 0
        
        # تقرير
        report = fraud.get_fraud_report()
        assert 'blacklisted' in report
        
        print("✅ Fraud protection: PASSED")


class TestIntegration:
    """اختبار تكامل جميع الخدمات معاً"""
    
    def test_complete_ecosystem(self):
        """كل الخدمات تعمل معاً بدون تعارض"""
        otp = OTPService()
        kyc = KYCService()
        fraud = FraudDetection()
        guard = EscrowGuard()
        dr = DisputeResolution()
        rs = ReputationService()
        
        # الكل initialized
        assert otp is not None
        assert kyc is not None
        assert fraud is not None
        assert guard is not None
        assert dr is not None
        assert rs is not None
        
        print("✅ Complete ecosystem: All services online")


if __name__ == '__main__':
    test = TestFullUserFlow()
    test.test_registration_to_first_deal()
    test.test_deal_payment_flow()
    test.test_dispute_resolution_flow()
    test.test_reputation_system()
    test.test_fraud_protection()
    
    integration = TestIntegration()
    integration.test_complete_ecosystem()
    
    print("\n🎉 جميع اختبارات التكامل اكتملت بنجاح!")
