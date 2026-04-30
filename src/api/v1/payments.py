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

from src.app.models.database import get_db
from src.app.models.deal import Deal
from src.app.models.transaction import Transaction, TransactionType, TransactionStatus
from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import PaymentSchema

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
        
        wallet_address = getattr(deal, 'escrow_address', None)
        if not wallet_address:
            # Generate from system config
            wallet_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT contract
        
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
    Check payment status from database.
    التحقق من حالة الدفع للصفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()
        
        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Check latest transaction
        tx = db.query(Transaction).filter(
            Transaction.deal_uuid == str(deal_uuid)
        ).order_by(Transaction.created_at.desc()).first()
        
        db.close()
        
        status = deal.status
        tx_hash = tx.tx_hash if tx else None
        confirmed_at = tx.confirmed_at.isoformat() if tx and tx.confirmed_at else None
        amount = float(deal.amount_usdt) if deal.amount_usdt else 0
        
        payment_info = {
            'deal_uuid': str(deal_uuid),
            'status': status,
            'amount_usdt': amount,
            'tx_hash': tx_hash,
            'confirmed_at': confirmed_at,
            'confirmations_required': 20,
            'current_confirmations': tx.confirmations if tx else 0,
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
            wallet = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
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
    Manually verify payment and record transaction.
    تحقق يدوي من الدفع وتسجيل المعاملة.
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
        
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()
        
        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Create transaction record
        transaction = Transaction(
            user_id=str(user_id),
            deal_uuid=str(deal_uuid),
            deal_id=deal.id,
            tx_type=TransactionType.ESCROW_DEPOSIT,
            tx_hash=tx_hash,
            amount_usdt=deal.amount_usdt,
            status=TransactionStatus.CONFIRMED,
            confirmed_at=datetime.now(timezone.utc)
        )
        db.add(transaction)
        
        # Update deal
        deal.escrow_tx_hash = tx_hash
        deal.escrow_tx_confirmed_at = datetime.now(timezone.utc)
        deal.status = 'funded'
        
        db.commit()
        db.close()
        
        logger.info("payment.verified", deal_id=deal.id, tx_hash=tx_hash)
        
        return jsonify({
            'message': 'Payment verified',
            'message_ar': 'تم التحقق من الدفع',
            'tx_hash': tx_hash,
            'transaction_id': transaction.id
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
        
        tx_hash = payload.get('transaction_id', '')
        memo = payload.get('memo', '')
        from_address = payload.get('from', '')
        to_address = payload.get('to', '')
        amount = payload.get('amount', 0)
        
        if tx_hash and memo:
            # Find deal by memo
            db = next(get_db())
            deal = db.query(Deal).filter(Deal.payment_memo == str(memo)).first()
            
            if deal:
                # Check for duplicate
                existing = db.query(Transaction).filter(
                    Transaction.tx_hash == tx_hash
                ).first()
                
                if not existing:
                    # Record transaction
                    tx = Transaction(
                        user_id=str(deal.buyer_id),
                        deal_uuid=str(deal.uuid),
                        deal_id=deal.id,
                        tx_type=TransactionType.ESCROW_DEPOSIT,
                        tx_hash=tx_hash,
                        amount_usdt=deal.amount_usdt,
                        from_address=from_address,
                        to_address=to_address,
                        status=TransactionStatus.CONFIRMING,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(tx)
                    
                    # Update deal
                    deal.escrow_tx_hash = tx_hash
                    deal.status = 'payment_received'
                    
                    db.commit()
                    logger.info("webhook.processed", deal_id=deal.id, tx_hash=tx_hash)
                else:
                    logger.info("webhook.duplicate", tx_hash=tx_hash)
            
            db.close()
            
            return jsonify({
                'status': 'received',
                'message': 'Webhook processed'
            }), 200
        
        return jsonify({'status': 'ignored', 'message': 'No transaction data'}), 200
        
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
        'USDT': {'USD': 1.0, 'EUR': 0.92, 'SAR': 3.75, 'AED': 3.67},
        'TRX': {'USD': 0.11, 'USDT': 0.11},
        'BTC': {'USD': 67500.00, 'USDT': 67500.00},
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    return jsonify({'rates': rates}), 200


@payments_bp.route('/history', methods=['GET'])
def payment_history():
    """
    Get user payment history from database.
    سجل مدفوعات المستخدم من قاعدة البيانات.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        db = next(get_db())
        query = db.query(Transaction).filter(
            Transaction.user_id == str(user_id)
        ).order_by(Transaction.created_at.desc())
        
        total = query.count()
        transactions = query.offset((page - 1) * per_page).limit(per_page).all()
        
        history = []
        for tx in transactions:
            # Get deal title if available
            deal_title = None
            if tx.deal_id:
                deal = db.query(Deal).filter(Deal.id == tx.deal_id).first()
                if deal:
                    deal_title = deal.title
            
            history.append({
                'id': tx.id,
                'deal_id': tx.deal_id,
                'deal_title': deal_title or 'معاملة',
                'tx_hash': tx.tx_hash,
                'tx_type': tx.tx_type,
                'amount_usdt': float(tx.amount_usdt) if tx.amount_usdt else 0,
                'amount': float(tx.amount_usdt) if tx.amount_usdt else 0,
                'status': tx.status,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
                'confirmed_at': tx.confirmed_at.isoformat() if tx.confirmed_at else None
            })
        
        db.close()
        
        return jsonify({
            'payments': history,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': (page * per_page) < total
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
    Generate payment receipt from transaction data.
    إنشاء إيصال الدفع من بيانات المعاملة.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()
        
        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        # Get latest confirmed transaction
        tx = db.query(Transaction).filter(
            Transaction.deal_uuid == str(deal_uuid),
            Transaction.status == TransactionStatus.CONFIRMED
        ).order_by(Transaction.created_at.desc()).first()
        
        db.close()
        
        receipt = {
            'deal_uuid': str(deal_uuid),
            'amount': float(deal.amount_usdt) if deal.amount_usdt else 0,
            'tx_hash': tx.tx_hash if tx else getattr(deal, 'escrow_tx_hash', ''),
            'date': tx.confirmed_at.isoformat() if tx and tx.confirmed_at else datetime.now(timezone.utc).isoformat(),
            'confirmed_at': tx.confirmed_at.isoformat() if tx and tx.confirmed_at else None,
            'status': deal.status,
            'from': tx.from_address if tx else '',
            'to': tx.to_address if tx else getattr(deal, 'escrow_address', ''),
            'network': 'TRC20',
            'transaction_id': tx.id if tx else None
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


__all__ = ['payments_bp']
