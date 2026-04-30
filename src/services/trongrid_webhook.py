"""
TronGrid Webhook Verification - SafeSend
التحقق من Webhook TronGrid - SafeSend

Verifies HMAC-SHA256 signatures from TronGrid webhooks.
يتحقق من توقيع HMAC-SHA256 من Webhooks TronGrid.
"""

import hmac
import hashlib
import os
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# Get webhook secret from environment
TRONGRID_WEBHOOK_SECRET = os.getenv("TRONGRID_WEBHOOK_SECRET", "")


def verify_trongrid_signature(payload: bytes, signature: str) -> bool:
    """
    Verify TronGrid webhook HMAC-SHA256 signature.
    التحقق من توقيع HMAC-SHA256 لـ TronGrid webhook.
    
    Args:
        payload: Raw request body / جسم الطلب الخام
        signature: X-TronGrid-Signature header
    
    Returns:
        bool: True if signature is valid
    """
    if not TRONGRID_WEBHOOK_SECRET:
        logger.warning("trongrid.webhook_secret_not_configured")
        # In development, allow without verification
        import os as _os
        if _os.getenv("FLASK_ENV", "development") == "development":
            return True
        return False
    
    if not signature:
        logger.warning("trongrid.missing_signature")
        return False
    
    try:
        expected = hmac.new(
            TRONGRID_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected, signature)
        
    except Exception as e:
        logger.error("trongrid.verification_error", error=str(e))
        return False


def extract_payment_info(payload: dict) -> Optional[dict]:
    """
    Extract payment information from TronGrid webhook payload.
    استخراج معلومات الدفع من حمولة TronGrid webhook.
    """
    try:
        return {
            'tx_hash': payload.get('transaction_id', ''),
            'from': payload.get('from', ''),
            'to': payload.get('to', ''),
            'amount': payload.get('amount', 0),
            'token': payload.get('token', 'USDT'),
            'memo': payload.get('memo', ''),
            'block': payload.get('block', 0),
            'confirmations': payload.get('confirmations', 0)
        }
    except Exception:
        return None


__all__ = [
    'verify_trongrid_signature',
    'extract_payment_info',
    'TRONGRID_WEBHOOK_SECRET'
]
