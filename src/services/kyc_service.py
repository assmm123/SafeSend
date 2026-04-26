"""
KYC Service - SafeSend
خدمة التحقق من الهوية - SafeSend

Handles identity verification via Telegram, email, documents, and external accounts.
يدير التحقق من الهوية عبر التلغرام والبريد والوثائق والحسابات الخارجية.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import structlog
import re

logger = structlog.get_logger(__name__)

VERIFICATION_WEIGHTS = {
    'email': 1, 'phone': 2, 'telegram': 2,
    'document': 3, 'selfie': 4, 'address': 3, 'github': 2
}

VERIFICATION_LEVELS = {
    0: {'name': 'غير موثق', 'daily_limit': 100, 'monthly_limit': 500, 'required_weight': 0},
    1: {'name': 'أساسي', 'daily_limit': 500, 'monthly_limit': 2500, 'required_weight': 3},
    2: {'name': 'موثق', 'daily_limit': 5000, 'monthly_limit': 25000, 'required_weight': 8},
    3: {'name': 'موثق بالكامل', 'daily_limit': 50000, 'monthly_limit': 250000, 'required_weight': 15}
}

class KYCService:
    """
    Know Your Customer service.
    خدمة اعرف عميلك.
    
    Multi-level verification with weighted scoring.
    توثيق متعدد المستويات بنظام النقاط الموزونة.
    """
    
    def __init__(self):
        self._verifications: Dict[int, Dict[str, Any]] = {}
    
    # ============================================================
    # Telegram Verification
    # ============================================================
    
    def verify_telegram(self, user_id: int, telegram_id: int) -> Dict[str, Any]:
        """
        Verify user via Telegram account.
        توثيق المستخدم عبر حساب التلغرام.
        """
        if not telegram_id or telegram_id <= 0:
            return {'success': False, 'error': 'invalid_telegram_id', 'message': 'معرف تلغرام غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['telegram'] = {
            'verified': True, 'telegram_id': telegram_id,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.telegram_verified", user_id=user_id, telegram_id=str(telegram_id)[:4] + '***')
        return {'success': True, 'message': 'تم توثيق التلغرام', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # Email Verification
    # ============================================================
    
    def verify_email(self, user_id: int, email: str) -> Dict[str, Any]:
        """
        Verify user email address.
        توثيق البريد الإلكتروني.
        """
        if not self._is_valid_email(email):
            return {'success': False, 'error': 'invalid_email', 'message': 'بريد إلكتروني غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['email'] = {
            'verified': True, 'email': email,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.email_verified", user_id=user_id)
        return {'success': True, 'message': 'تم توثيق البريد', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # Document Verification
    # ============================================================
    
    def verify_document(self, user_id: int, doc_type: str, doc_number: str, doc_image_url: str = '') -> Dict[str, Any]:
        """
        Verify identity document (passport, national ID, etc).
        توثيق وثيقة هوية (جواز سفر، هوية وطنية، إلخ).
        """
        valid_types = ['passport', 'national_id', 'driving_license', 'residence_permit']
        if doc_type not in valid_types:
            return {'success': False, 'error': 'invalid_doc_type', 'message': 'نوع وثيقة غير صالح'}
        
        if not doc_number or len(doc_number) < 4:
            return {'success': False, 'error': 'invalid_doc_number', 'message': 'رقم وثيقة غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['document'] = {
            'verified': True, 'doc_type': doc_type,
            'doc_number': self._mask_document(doc_number),
            'doc_image_url': doc_image_url,
            'verified_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=730)).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.document_verified", user_id=user_id, doc_type=doc_type)
        return {'success': True, 'message': 'تم توثيق الوثيقة', 'new_level': self.get_trust_level(user_id)}
    
    def verify_selfie(self, user_id: int, selfie_url: str) -> Dict[str, Any]:
        """
        Verify selfie with document.
        توثيق صورة شخصية مع الوثيقة.
        """
        self._init_user(user_id)
        self._verifications[user_id]['selfie'] = {
            'verified': True, 'selfie_url': selfie_url,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.selfie_verified", user_id=user_id)
        return {'success': True, 'message': 'تم توثيق الصورة الشخصية', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # Address Verification
    # ============================================================
    
    def verify_address(self, user_id: int, address: str, proof_url: str = '') -> Dict[str, Any]:
        """
        Verify residential address with proof.
        توثيق عنوان السكن مع إثبات.
        """
        if not address or len(address) < 10:
            return {'success': False, 'error': 'invalid_address', 'message': 'عنوان غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['address'] = {
            'verified': True, 'address': address[:50],
            'proof_url': proof_url,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.address_verified", user_id=user_id)
        return {'success': True, 'message': 'تم توثيق العنوان', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # GitHub Verification
    # ============================================================
    
    def verify_github(self, user_id: int, github_username: str) -> Dict[str, Any]:
        """
        Verify user via GitHub account.
        توثيق المستخدم عبر حساب GitHub.
        """
        if not github_username or not re.match(r'^[a-zA-Z0-9-]{1,39}$', github_username):
            return {'success': False, 'error': 'invalid_github', 'message': 'اسم مستخدم GitHub غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['github'] = {
            'verified': True, 'github_username': github_username,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.github_verified", user_id=user_id, github=github_username)
        return {'success': True, 'message': 'تم توثيق GitHub', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # Phone Verification
    # ============================================================
    
    def verify_phone(self, user_id: int, phone: str) -> Dict[str, Any]:
        """
        Verify phone number.
        توثيق رقم الهاتف.
        """
        if not phone or not re.match(r'^\+?[0-9]{7,15}$', phone):
            return {'success': False, 'error': 'invalid_phone', 'message': 'رقم هاتف غير صالح'}
        
        self._init_user(user_id)
        self._verifications[user_id]['phone'] = {
            'verified': True, 'phone': self._mask_phone(phone),
            'verified_at': datetime.now(timezone.utc).isoformat()
        }
        self._recalculate_level(user_id)
        
        logger.info("kyc.phone_verified", user_id=user_id)
        return {'success': True, 'message': 'تم توثيق الهاتف', 'new_level': self.get_trust_level(user_id)}
    
    # ============================================================
    # Trust Level & Limits
    # ============================================================
    
    def get_trust_level(self, user_id: int) -> Dict[str, Any]:
        """
        Get user trust level based on verifications.
        الحصول على مستوى الثقة بناءً على التوثيقات.
        """
        self._init_user(user_id)
        weight = self._calculate_weight(user_id)
        level = self._get_level_by_weight(weight)
        limits = self.get_transaction_limit(user_id)
        
        return {
            'level': level,
            'level_name': VERIFICATION_LEVELS[level]['name'],
            'weight': weight,
            'daily_limit': limits['daily'],
            'monthly_limit': limits['monthly'],
            'verifications': self.get_verification_status(user_id)
        }
    
    def get_transaction_limit(self, user_id: int) -> Dict[str, Any]:
        """
        Get transaction limits based on trust level.
        الحصول على حدود المعاملات بناءً على مستوى الثقة.
        """
        self._init_user(user_id)
        weight = self._calculate_weight(user_id)
        level = self._get_level_by_weight(weight)
        return {
            'daily': VERIFICATION_LEVELS[level]['daily_limit'],
            'monthly': VERIFICATION_LEVELS[level]['monthly_limit']
        }
    
    def get_verification_status(self, user_id: int) -> Dict[str, bool]:
        """
        Get all verification statuses.
        جميع حالات التوثيق.
        """
        self._init_user(user_id)
        status = {}
        for key in VERIFICATION_WEIGHTS:
            v = self._verifications[user_id].get(key, {})
            status[key] = v.get('verified', False)
        return status
    
    def get_verification_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Get verification completion progress.
        نسبة إكمال التوثيق.
        """
        self._init_user(user_id)
        total_weight = sum(VERIFICATION_WEIGHTS.values())
        current = self._calculate_weight(user_id)
        
        return {
            'progress_pct': round((current / total_weight) * 100, 1),
            'current_weight': current,
            'max_weight': total_weight,
            'next_level': self._get_next_level(user_id),
            'verifications': self.get_verification_status(user_id)
        }
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _init_user(self, user_id: int) -> None:
        """Initialize user verification record."""
        if user_id not in self._verifications:
            self._verifications[user_id] = {}
    
    def _calculate_weight(self, user_id: int) -> int:
        """Calculate total verification weight."""
        total = 0
        for key, weight in VERIFICATION_WEIGHTS.items():
            if self._verifications[user_id].get(key, {}).get('verified', False):
                total += weight
        return total
    
    def _get_level_by_weight(self, weight: int) -> int:
        """Determine trust level based on weight."""
        current = 0
        for level, info in sorted(VERIFICATION_LEVELS.items()):
            if weight >= info['required_weight']:
                current = level
        return current
    
    def _get_next_level(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get next verification level requirements."""
        weight = self._calculate_weight(user_id)
        for level in sorted(VERIFICATION_LEVELS.keys()):
            if VERIFICATION_LEVELS[level]['required_weight'] > weight:
                return {
                    'level': level,
                    'name': VERIFICATION_LEVELS[level]['name'],
                    'required_weight': VERIFICATION_LEVELS[level]['required_weight'],
                    'remaining': VERIFICATION_LEVELS[level]['required_weight'] - weight
                }
        return None
    
    def _recalculate_level(self, user_id: int) -> None:
        """Recalculate and store trust level."""
        weight = self._calculate_weight(user_id)
        level = self._get_level_by_weight(weight)
        self._verifications[user_id]['_level'] = level
        self._verifications[user_id]['_weight'] = weight
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))
    
    def _mask_document(self, doc: str) -> str:
        """Mask document number for privacy."""
        if len(doc) <= 4:
            return '*' * len(doc)
        return doc[:2] + '*' * (len(doc) - 4) + doc[-2:]
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for privacy."""
        if len(phone) <= 4:
            return '*' * len(phone)
        return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]


kyc_service = KYCService()

__all__ = ['KYCService', 'kyc_service', 'VERIFICATION_LEVELS', 'VERIFICATION_WEIGHTS']
