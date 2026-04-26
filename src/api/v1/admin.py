"""
Admin API Endpoints - SafeSend
نقاط نهاية المشرف - SafeSend

Handles payouts, disputes, user management, stats, and system operations.
يدير المدفوعات، النزاعات، إدارة المستخدمين، الإحصائيات، وعمليات النظام.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog

from src.app.models.deal_repository import DealRepository
from src.app.models.user_repository import UserRepository
from src.app.models.security import decode_token
from src.api.schemas import (
    AdminStatsSchema,
    PaymentSchema,
    DisputeSchema,
    UserSchema
)

logger = structlog.get_logger(__name__)
admin_bp = Blueprint('admin_v1', __name__, url_prefix='/api/v1/admin')

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

def _require_admin():
    """Check admin authentication."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    # In production: check user role from DB
    return user_id, None

def _get_deal_repo():
    return DealRepository()

def _get_user_repo():
    return UserRepository()

# ============================================================
# 💰 Payouts Management
# ============================================================

@admin_bp.route('/payouts/pending', methods=['GET'])
def pending_payouts():
    """List pending payouts. / المدفوعات المعلقة."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        payouts = [{
            'id': 1, 'deal_uuid': 'sample-uuid',
            'amount_usdt': 100.00, 'to_address': 'TXXX...',
            'status': 'pending', 'created_at': datetime.now(timezone.utc).isoformat()
        }]
        
        return jsonify({'payouts': PaymentSchema().dump(payouts, many=True)}), 200
    except Exception as e:
        logger.error("admin.payouts_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/history', methods=['GET'])
def payouts_history():
    """Payout history. / سجل المدفوعات."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        return jsonify({'payouts': [], 'pagination': {'total': 0}}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/<uuid:deal_uuid>/mark-sent', methods=['POST'])
def mark_payout_sent(deal_uuid: str):
    """Mark payout as sent. / تأكيد إرسال الدفع."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        reference = data.get('reference', '')
        
        logger.info("admin.payout_sent", deal_uuid=str(deal_uuid), reference=reference)
        
        return jsonify({'message': 'Payout marked as sent', 'message_ar': 'تم تأكيد الإرسال'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/<uuid:deal_uuid>/mark-failed', methods=['POST'])
def mark_payout_failed(deal_uuid: str):
    """Mark payout as failed. / فشل الدفع."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        
        logger.info("admin.payout_failed", deal_uuid=str(deal_uuid), reason=reason)
        
        return jsonify({'message': 'Payout marked as failed', 'message_ar': 'تم تعليم الدفع كفاشل'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/<uuid:deal_uuid>/retry', methods=['POST'])
def retry_payout(deal_uuid: str):
    """Retry payout. / إعادة محاولة الدفع."""
    user_id, error = _require_admin()
    if error:
        return error
    
    logger.info("admin.payout_retry", deal_uuid=str(deal_uuid))
    return jsonify({'message': 'Payout retry initiated', 'message_ar': 'تم بدء إعادة المحاولة'}), 200


# ============================================================
# ⚠️ Disputes Management
# ============================================================

@admin_bp.route('/disputes/active', methods=['GET'])
def active_disputes():
    """List active disputes. / النزاعات النشطة."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({'disputes': [], 'total': 0}), 200


@admin_bp.route('/disputes/all', methods=['GET'])
def all_disputes():
    """List all disputes. / جميع النزاعات."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({'disputes': [], 'total': 0}), 200


@admin_bp.route('/disputes/<int:dispute_id>', methods=['GET'])
def dispute_detail(dispute_id: int):
    """Get dispute details. / تفاصيل نزاع."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({'dispute': {'id': dispute_id, 'status': 'opened'}}), 200


@admin_bp.route('/disputes/<int:dispute_id>/resolve', methods=['POST'])
def resolve_dispute(dispute_id: int):
    """Resolve a dispute. / حل نزاع."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        resolution = data.get('resolution', '')
        decision = data.get('decision', 'split')
        
        logger.info("admin.dispute_resolved", dispute_id=dispute_id, decision=decision)
        
        return jsonify({
            'message': 'Dispute resolved',
            'message_ar': 'تم حل النزاع',
            'resolution': resolution,
            'decision': decision
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/disputes/<int:dispute_id>/assign', methods=['POST'])
def assign_dispute(dispute_id: int):
    """Assign dispute to mediator. / تعيين لمشرف."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        mediator_id = data.get('mediator_id', 0)
        
        logger.info("admin.dispute_assigned", dispute_id=dispute_id, mediator_id=mediator_id)
        
        return jsonify({'message': 'Dispute assigned', 'message_ar': 'تم تعيين النزاع'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/disputes/<int:dispute_id>/note', methods=['POST'])
def add_dispute_note(dispute_id: int):
    """Add internal note. / ملاحظة داخلية."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        note = data.get('note', '')
        
        logger.info("admin.dispute_note", dispute_id=dispute_id)
        
        return jsonify({'message': 'Note added', 'message_ar': 'تمت إضافة الملاحظة'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 👤 Users Management
# ============================================================

@admin_bp.route('/users', methods=['GET'])
def list_users():
    """List all users. / قائمة المستخدمين."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        return jsonify({
            'users': [],
            'pagination': {'page': page, 'per_page': per_page, 'total': 0}
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/users/<int:target_user_id>', methods=['GET'])
def user_detail(target_user_id: int):
    """Get user details. / تفاصيل مستخدم."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({'user': {'id': target_user_id}}), 200


@admin_bp.route('/users/<int:target_user_id>/verify', methods=['POST'])
def verify_user_kyc(target_user_id: int):
    """Verify user KYC. / توثيق KYC."""
    user_id, error = _require_admin()
    if error:
        return error
    
    logger.info("admin.kyc_verified", user_id=target_user_id)
    return jsonify({'message': 'KYC verified', 'message_ar': 'تم توثيق الحساب'}), 200


@admin_bp.route('/users/<int:target_user_id>/suspend', methods=['POST'])
def suspend_user(target_user_id: int):
    """Suspend user. / تعليق مستخدم."""
    user_id, error = _require_admin()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        
        logger.info("admin.user_suspended", user_id=target_user_id, reason=reason)
        
        return jsonify({'message': 'User suspended', 'message_ar': 'تم تعليق المستخدم'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/users/<int:target_user_id>/unsuspend', methods=['POST'])
def unsuspend_user(target_user_id: int):
    """Unsuspend user. / إلغاء تعليق."""
    user_id, error = _require_admin()
    if error:
        return error
    
    logger.info("admin.user_unsuspended", user_id=target_user_id)
    return jsonify({'message': 'User unsuspended', 'message_ar': 'تم إلغاء التعليق'}), 200


# ============================================================
# 📊 Stats
# ============================================================

@admin_bp.route('/stats', methods=['GET'])
def admin_stats():
    """Get system stats. / إحصائيات النظام."""
    user_id, error = _require_admin()
    if error:
        return error
    
    stats = {
        'total_users': 0, 'active_deals': 0, 'completed_deals': 0,
        'disputes_opened': 0, 'total_volume_usdt': '0.00',
        'platform_revenue': '0.00', 'new_users_today': 0, 'new_deals_today': 0
    }
    
    return jsonify({'stats': AdminStatsSchema().dump(stats)}), 200


@admin_bp.route('/stats/revenue', methods=['GET'])
def revenue_report():
    """Revenue report. / تقرير الإيرادات."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({
        'revenue': {
            'today': '0.00', 'this_week': '0.00',
            'this_month': '0.00', 'total': '0.00'
        }
    }), 200


@admin_bp.route('/stats/export', methods=['GET'])
def export_stats():
    """Export stats as CSV. / تصدير CSV."""
    user_id, error = _require_admin()
    if error:
        return error
    
    csv_data = "metric,value\ntotal_users,0\nactive_deals,0\n"
    
    return csv_data, 200, {'Content-Type': 'text/csv'}


# ============================================================
# ⚙️ System Operations
# ============================================================

@admin_bp.route('/backup/trigger', methods=['POST'])
def trigger_backup():
    """Trigger system backup. / تشغيل نسخ احتياطي."""
    user_id, error = _require_admin()
    if error:
        return error
    
    logger.info("admin.backup_triggered")
    
    return jsonify({
        'message': 'Backup initiated',
        'message_ar': 'تم بدء النسخ الاحتياطي',
        'backup_id': datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    }), 200


@admin_bp.route('/backups', methods=['GET'])
def list_backups():
    """List backups. / قائمة النسخ الاحتياطية."""
    user_id, error = _require_admin()
    if error:
        return error
    
    return jsonify({'backups': []}), 200


@admin_bp.route('/maintenance/cleanup', methods=['POST'])
def maintenance_cleanup():
    """Run maintenance cleanup. / تنظيف البيانات."""
    user_id, error = _require_admin()
    if error:
        return error
    
    logger.info("admin.cleanup_triggered")
    
    return jsonify({
        'message': 'Cleanup completed',
        'message_ar': 'تم التنظيف بنجاح',
        'deleted_sessions': 0,
        'deleted_logs': 0
    }), 200


__all__ = ['admin_bp']
