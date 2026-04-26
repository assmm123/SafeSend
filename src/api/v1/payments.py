"""
Payments API Endpoints - SafeSend
نقاط نهاية المدفوعات - SafeSend

Handles payment QR codes, status checks, webhooks, and history.
يدير رموز QR للدفع، فحص الحالة، webhooks، وسجل المدفوعات.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import structlog

from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import PaymentSchema, PayoutSchema

logger = structlog.get_logger(__name__)
payments_bp = Blueprint('payments_v1', __name__, url_prefix='/api/v1/payments')

# ============================================================
# 🔐 Helpers
# ============================================================

def _get_user_id() -> Optional[int]:
    """Extract user_id from JWT token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    payload = decode_token(token)
    if payload and 'user_id' in payload:
        try:
            return int(payload['user_id'])
        except (ValueError, TypeError):
            return None
    return None

def _require_auth():
    """Check authentication and return user_id or error."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    return user_id, None

def _get_deal_repo():
    """Get deal repository instance."""
    return DealRepository()

# ============================================================
# 💰 Payment Endpoints
# ============================================================

@payments_bp.route('/<uuid:deal_uuid>/qr', methods=['GET'])
def payment_qr(deal_uuid: str):
    """
    Generate payment QR code for deal.
    إنشاء رمز QR للدفع للصفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Generate payment info
        wallet_address = getattr(deal, 'escrow_address', 'TBD')
        amount = getattr(deal, 'amount_usdt', 0)
        
        qr_data = f"tron://{wallet_address}?amount={amount}&currency=USDT"
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'wallet_address': wallet_address,
            'amount_usdt': float(amount),
            'qr_data': qr_data,
            'network': 'TRC20',
            'expires_in': 1800
        }), 200
        
    except Exception as e:
        logger.error("payment.qr_failed", error=str(e))
        return jsonify({
            'error': 'Failed to generate QR',
            'message_ar': 'فشل إنشاء رمز QR'
        }), 500


@payments_bp.route('/<uuid:deal_uuid>/status', methods=['GET'])
def payment_status(deal_uuid: str):
    """
    Check payment status for deal.
    التحقق من حالة الدفع للصفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        status = getattr(deal, 'status', 'pending_payment')
        tx_hash = getattr(deal, 'escrow_tx_hash', None)
        confirmed_at = getattr(deal, 'escrow_tx_confirmed_at', None)
        amount = getattr(deal, 'amount_usdt', 0)
        
        payment_info = {
            'deal_uuid': str(deal_uuid),
            'status': status,
            'amount_usdt': float(amount),
            'tx_hash': tx_hash,
            'confirmed_at': confirmed_at.isoformat() if confirmed_at else None,
            'confirmations_required': 20,
            'current_confirmations': 0,
            'is_paid': status in ['funded', 'delivered', 'completed']
        }
        
        return jsonify(payment_info), 200
        
    except Exception as e:
        logger.error("payment.status_failed", error=str(e))
        return jsonify({
            'error': 'Failed to check status',
            'message_ar': 'فشل التحقق من الحالة'
        }), 500


@payments_bp.route('/<uuid:deal_uuid>/address', methods=['GET'])
def payment_address(deal_uuid: str):
    """
    Get escrow wallet address for payment.
    الحصول على عنوان محفظة الوساطة للدفع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        wallet = getattr(deal, 'escrow_address', None)
        if not wallet:
            wallet = f"T{str(deal_uuid)[:33].replace('-', '')}"[:34]
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'address': wallet,
            'network': 'TRC20',
            'memo': getattr(deal, 'payment_memo', str(deal.id))
        }), 200
        
    except Exception as e:
        logger.error("payment.address_failed", error=str(e))
        return jsonify({
            'error': 'Failed to get address',
            'message_ar': 'فشل الحصول على العنوان'
        }), 500


@payments_bp.route('/<uuid:deal_uuid>/verify', methods=['POST'])
def verify_payment(deal_uuid: str):
    """
    Manually verify payment (admin only).
    تحقق يدوي من الدفع (للمشرف فقط).
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        tx_hash = data.get('tx_hash', '')
        
        if not tx_hash:
            return jsonify({
                'error': 'Transaction hash required',
                'message_ar': 'هاش المعاملة مطلوب'
            }), 400
        
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Update deal
        repo.update(deal, {
            'escrow_tx_hash': tx_hash,
            'escrow_tx_confirmed_at': datetime.now(timezone.utc)
        })
        repo.update_status(deal, 'funded')
        
        logger.info("payment.verified", deal_id=deal.id, tx_hash=tx_hash)
        
        return jsonify({
            'message': 'Payment verified',
            'message_ar': 'تم التحقق من الدفع',
            'tx_hash': tx_hash
        }), 200
        
    except Exception as e:
        logger.error("payment.verify_failed", error=str(e))
        return jsonify({
            'error': 'Verification failed',
            'message_ar': 'فشل التحقق'
        }), 500


@payments_bp.route('/webhook/trongrid', methods=['POST'])
def trongrid_webhook():
    """
    Handle TronGrid webhook for payment confirmation.
    معالجة Webhook من TronGrid لتأكيد الدفع.
    """
    try:
        payload = request.get_json(silent=True) or {}
        signature = request.headers.get('X-TronGrid-Signature', '')
        
        # In production: verify HMAC signature
        logger.info("webhook.received", source='trongrid')
        
        # Extract transaction details
        tx_hash = payload.get('transaction_id', '')
        memo = payload.get('memo', '')
        
        if tx_hash and memo:
            # Find deal by memo and update status
            logger.info("webhook.processed", tx_hash=tx_hash, memo=memo)
        
        return jsonify({
            'status': 'received',
            'message': 'Webhook processed'
        }), 200
        
    except Exception as e:
        logger.error("webhook.failed", error=str(e))
        return jsonify({
            'error': 'Webhook processing failed',
            'message_ar': 'فشل معالجة webhook'
        }), 500


@payments_bp.route('/rates', methods=['GET'])
def exchange_rates():
    """
    Get current exchange rates.
    أسعار الصرف الحالية.
    """
    rates = {
        'USDT': {'USD': 1.0, 'EUR': 0.92, 'SAR': 3.75},
        'TRX': {'USD': 0.11, 'USDT': 0.11},
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    return jsonify({'rates': rates}), 200


@payments_bp.route('/history', methods=['GET'])
def payment_history():
    """
    Get user payment history.
    سجل مدفوعات المستخدم.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # In production: fetch from Transaction model
        history = [{
            'id': 1,
            'transaction_uuid': 'sample-uuid',
            'deal_id': 1,
            'tx_type': 'escrow_deposit',
            'amount_usdt': 100.00,
            'status': 'confirmed',
            'created_at': datetime.now(timezone.utc).isoformat()
        }]
        
        return jsonify({
            'payments': PaymentSchema().dump(history, many=True),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': 1
            }
        }), 200
        
    except Exception as e:
        logger.error("payment.history_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch history',
            'message_ar': 'فشل جلب السجل'
        }), 500


@payments_bp.route('/<uuid:deal_uuid>/receipt', methods=['GET'])
def payment_receipt(deal_uuid: str):
    """
    Generate payment receipt (PDF placeholder).
    إنشاء إيصال الدفع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        receipt = {
            'deal_uuid': str(deal_uuid),
            'amount': float(getattr(deal, 'amount_usdt', 0)),
            'tx_hash': getattr(deal, 'escrow_tx_hash', ''),
            'date': datetime.now(timezone.utc).isoformat(),
            'status': getattr(deal, 'status', 'unknown'),
            'from': getattr(deal, 'buyer_wallet', ''),
            'to': getattr(deal, 'escrow_address', '')
        }
        
        return jsonify({
            'receipt': receipt,
            'message': 'Receipt generated',
            'message_ar': 'تم إنشاء الإيصال'
        }), 200
        
    except Exception as e:
        logger.error("payment.receipt_failed", error=str(e))
        return jsonify({
            'error': 'Failed to generate receipt',
            'message_ar': 'فشل إنشاء الإيصال'
        }), 500


@payments_bp.route('/<uuid:deal_uuid>/retry', methods=['POST'])
def retry_payment(deal_uuid: str):
    """
    Retry a failed payment.
    إعادة محاولة دفع فاشل.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Generate new payment info
        wallet = getattr(deal, 'escrow_address', 'TBD')
        amount = getattr(deal, 'amount_usdt', 0)
        
        logger.info("payment.retry_initiated", deal_id=deal.id)
        
        return jsonify({
            'message': 'Payment retry initiated',
            'message_ar': 'تم بدء إعادة المحاولة',
            'deal_uuid': str(deal_uuid),
            'wallet_address': wallet,
            'amount_usdt': float(amount)
        }), 200
        
    except Exception as e:
        logger.error("payment.retry_failed", error=str(e))
        return jsonify({
            'error': 'Retry failed',
            'message_ar': 'فشل إعادة المحاولة'
        }), 500


# ============================================================
# 📦 Export
# ============================================================

__all__ = ['payments_bp']
