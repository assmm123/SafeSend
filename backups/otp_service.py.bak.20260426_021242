"""
OTP Service - SafeSend
خدمة كلمات المرور لمرة واحدة - SafeSend

Handles OTP generation, verification via email/telegram, and TOTP 2FA.
يدير توليد رموز OTP والتحقق منها عبر البريد والتلغرام وTOTP.
"""

import secrets
import hashlib
import time
import structlog
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List

logger = structlog.get_logger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 300
MAX_ATTEMPTS = 3
BLOCK_DURATION_MINUTES = 15
RATE_LIMIT_SECONDS = 60
BACKUP_CODES_COUNT = 8

class OTPService:
    """
    One-Time Password and 2FA service.
    خدمة كلمات المرور لمرة واحدة والمصادقة الثنائية.
    """
    
    def __init__(self):
        self._otp_store: Dict[str, Dict[str, Any]] = {}
        self._attempts: Dict[str, int] = {}
        self._blocked: Dict[str, float] = {}
        self._last_sent: Dict[str, float] = {}
    
    # ============================================================
    # OTP Generation
    # ============================================================
    
    def generate_otp(self, length: int = OTP_LENGTH) -> str:
        """
        Generate a random numeric OTP.
        توليد رمز OTP رقمي عشوائي.
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def generate_totp_secret(self) -> str:
        """
        Generate TOTP secret for Google Authenticator.
        توليد سر TOTP لـ Google Authenticator.
        """
        import base64
        return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
    
    def generate_backup_codes(self, count: int = BACKUP_CODES_COUNT) -> List[str]:
        """
        Generate backup recovery codes.
        توليد رموز استرداد احتياطية.
        """
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    # ============================================================
    # Send OTP
    # ============================================================
    
    def send_email_otp(self, user_id: int, email: str) -> Dict[str, Any]:
        """
        Send OTP via email with rate limiting.
        إرسال رمز OTP عبر البريد مع تحديد المعدل.
        """
        key = f"email:{user_id}"
        
        if not self._check_rate_limit(key):
            return {'success': False, 'error': 'rate_limited', 'message': 'يرجى الانتظار 60 ثانية'}
        
        otp = self.generate_otp()
        self._otp_store[key] = {
            'code': self._hash_otp(otp),
            'expires_at': time.time() + OTP_EXPIRY_SECONDS,
            'type': 'email',
            'user_id': user_id,
            'sent_to': email
        }
        self._last_sent[key] = time.time()
        
        logger.info("otp.email_sent", user_id=user_id, email=email[:3] + '***')
        
        return {'success': True, 'otp': otp, 'expires_in': OTP_EXPIRY_SECONDS}
    
    def send_telegram_otp(self, user_id: int, telegram_id: int) -> Dict[str, Any]:
        """
        Send OTP via Telegram with rate limiting.
        إرسال رمز OTP عبر التلغرام مع تحديد المعدل.
        """
        key = f"telegram:{user_id}"
        
        if not self._check_rate_limit(key):
            return {'success': False, 'error': 'rate_limited', 'message': 'يرجى الانتظار 60 ثانية'}
        
        otp = self.generate_otp()
        self._otp_store[key] = {
            'code': self._hash_otp(otp),
            'expires_at': time.time() + OTP_EXPIRY_SECONDS,
            'type': 'telegram',
            'user_id': user_id,
            'sent_to': str(telegram_id)
        }
        self._last_sent[key] = time.time()
        
        logger.info("otp.telegram_sent", user_id=user_id)
        
        return {'success': True, 'otp': otp, 'expires_in': OTP_EXPIRY_SECONDS}
    
    # ============================================================
    # Verify OTP
    # ============================================================
    
    def verify_otp(self, user_id: int, code: str, channel: str = 'email') -> Dict[str, Any]:
        """
        Verify OTP code with attempt limiting.
        التحقق من رمز OTP مع تحديد المحاولات.
        """
        key = f"{channel}:{user_id}"
        
        # Check if blocked
        if self._is_blocked(key):
            remaining = int(self._blocked[key] - time.time())
            return {
                'success': False,
                'error': 'blocked',
                'message': f'محظور. حاول بعد {remaining} ثانية',
                'remaining_seconds': max(0, remaining)
            }
        
        stored = self._otp_store.get(key)
        
        if not stored:
            return {'success': False, 'error': 'no_otp', 'message': 'لم يتم طلب رمز تحقق'}
        
        if time.time() > stored['expires_at']:
            del self._otp_store[key]
            return {'success': False, 'error': 'expired', 'message': 'انتهت صلاحية الرمز'}
        
        if self._hash_otp(code) != stored['code']:
            self._increment_attempts(key)
            remaining = self.get_remaining_attempts(key)
            return {
                'success': False,
                'error': 'invalid',
                'message': f'رمز غير صحيح. {remaining} محاولات متبقية',
                'remaining_attempts': remaining
            }
        
        # Success
        del self._otp_store[key]
        self._reset_attempts(key)
        logger.info("otp.verified", user_id=user_id, channel=channel)
        
        return {'success': True, 'message': 'تم التحقق بنجاح'}
    
    # ============================================================
    # TOTP (Google Authenticator)
    # ============================================================
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """
        Verify TOTP code (Google Authenticator).
        التحقق من رمز TOTP (Google Authenticator).
        """
        import pyotp
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code)
        except Exception as e:
            logger.error("totp.verify_failed", error=str(e))
            return False
    
    def generate_totp_uri(self, secret: str, email: str, issuer: str = 'SafeSend') -> str:
        """
        Generate TOTP provisioning URI for QR code.
        توليد رابط إعداد TOTP لرمز QR.
        """
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    # ============================================================
    # Rate Limiting & Security
    # ============================================================
    
    def _check_rate_limit(self, key: str) -> bool:
        """Check if rate limit allows new OTP request."""
        last = self._last_sent.get(key, 0)
        return (time.time() - last) >= RATE_LIMIT_SECONDS
    
    def _increment_attempts(self, key: str) -> None:
        """Increment failed attempts count."""
        self._attempts[key] = self._attempts.get(key, 0) + 1
        if self._attempts[key] >= MAX_ATTEMPTS:
            self._blocked[key] = time.time() + (BLOCK_DURATION_MINUTES * 60)
            logger.warning("otp.blocked", key=key, attempts=self._attempts[key])
    
    def _reset_attempts(self, key: str) -> None:
        """Reset failed attempts count."""
        self._attempts.pop(key, None)
        self._blocked.pop(key, None)
    
    def _is_blocked(self, key: str) -> bool:
        """Check if user is currently blocked."""
        return key in self._blocked and time.time() < self._blocked[key]
    
    def get_remaining_attempts(self, key: str) -> int:
        """Get remaining verification attempts."""
        return max(0, MAX_ATTEMPTS - self._attempts.get(key, 0))
    
    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage."""
        return hashlib.sha256(f"{otp}:safesend_salt".encode()).hexdigest()
    
    # ============================================================
    # Cleanup
    # ============================================================
    
    def cleanup_expired(self) -> int:
        """Remove expired OTPs. / حذف الرموز المنتهية."""
        now = time.time()
        expired_keys = [k for k, v in self._otp_store.items() if v['expires_at'] < now]
        for key in expired_keys:
            del self._otp_store[key]
        return len(expired_keys)
    
    def revoke_all(self, user_id: int) -> int:
        """Revoke all active OTPs for a user. / إلغاء جميع الرموز النشطة."""
        count = 0
        for key in list(self._otp_store.keys()):
            if str(user_id) in key:
                del self._otp_store[key]
                count += 1
        return count


# Create singleton instance
otp_service = OTPService()

__all__ = ['OTPService', 'otp_service', 'OTP_EXPIRY_SECONDS', 'MAX_ATTEMPTS']
