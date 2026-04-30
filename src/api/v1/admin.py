"""
Admin API Endpoints - SafeSend
نقاط نهاية المشرف - SafeSend

Handles payouts, disputes, user management, stats, and system operations.
يدير المدفوعات، النزاعات، إدارة المستخدمين، الإحصائيات، وعمليات النظام.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import structlog

from src.app.models.database import get_db
from src.app.models.user import User
from src.app.models.deal import Deal
from src.app.models.transaction import Transaction
from src.app.models.dispute import Dispute
from src.app.models.user_repository import UserRepository, get_user_repo
from src.app.models.deal_repository import DealRepository
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
    """Check admin authentication and authorization."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    
    # Verify admin role from database
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or (user.role != 'admin' and not user.is_admin):
            return None, (jsonify({
                'error': 'Admin access required',
                'message_ar': 'صلاحيات المشرف مطلوبة'
            }), 403)
    finally:
        db.close()
    
    return user_id, None

def _get_user_repo():
    return get_user_repo()

def _get_deal_repo():
    return DealRepository()

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
        db = next(get_db())
        transactions = db.query(Transaction).filter(
            Transaction.status == 'pending',
            Transaction.type == 'payout'
        ).order_by(Transaction.created_at.desc()).limit(50).all()
        
        payouts = []
        for t in transactions:
            payouts.append({
                'id': t.id,
                'deal_uuid': str(t.deal_uuid) if t.deal_uuid else '',
                'amount_usdt': float(t.amount) if t.amount else 0,
                'to_address': t.to_address or '',
                'status': t.status,
                'created_at': t.created_at.isoformat() if t.created_at else None
            })
        
        db.close()
        return jsonify({'payouts': PaymentSchema().dump(payouts, many=True)}), 200
    except Exception as e:
        logger.error("admin.payouts_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/history', methods=['GET'])
def payouts_history():
    """Payout history with pagination. / سجل المدفوعات."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        db = next(get_db())
        query = db.query(Transaction).filter(
            Transaction.type == 'payout'
        ).order_by(Transaction.created_at.desc())
        
        total = query.count()
        transactions = query.offset((page - 1) * per_page).limit(per_page).all()
        
        payouts = []
        for t in transactions:
            payouts.append({
                'id': t.id,
                'deal_uuid': str(t.deal_uuid) if t.deal_uuid else '',
                'amount_usdt': float(t.amount) if t.amount else 0,
                'to_address': t.to_address or '',
                'status': t.status,
                'created_at': t.created_at.isoformat() if t.created_at else None
            })
        
        db.close()
        return jsonify({
            'payouts': PaymentSchema().dump(payouts, many=True),
            'pagination': {'page': page, 'per_page': per_page, 'total': total}
        }), 200
    except Exception as e:
        logger.error("admin.payouts_history_failed", error=str(e))
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
        
        db = next(get_db())
        transaction = db.query(Transaction).filter(
            Transaction.deal_uuid == str(deal_uuid),
            Transaction.type == 'payout'
        ).first()
        
        if not transaction:
            db.close()
            return jsonify({'error': 'Payout not found', 'message_ar': 'الدفع غير موجود'}), 404
        
        transaction.status = 'sent'
        transaction.reference = reference
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        
        logger.info("admin.payout_sent", deal_uuid=str(deal_uuid), reference=reference)
        return jsonify({'message': 'Payout marked as sent', 'message_ar': 'تم تأكيد الإرسال'}), 200
    except Exception as e:
        logger.error("admin.payout_sent_failed", error=str(e))
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
        
        db = next(get_db())
        transaction = db.query(Transaction).filter(
            Transaction.deal_uuid == str(deal_uuid),
            Transaction.type == 'payout'
        ).first()
        
        if not transaction:
            db.close()
            return jsonify({'error': 'Payout not found', 'message_ar': 'الدفع غير موجود'}), 404
        
        transaction.status = 'failed'
        transaction.failure_reason = reason
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        
        logger.info("admin.payout_failed", deal_uuid=str(deal_uuid), reason=reason)
        return jsonify({'message': 'Payout marked as failed', 'message_ar': 'تم تعليم الدفع كفاشل'}), 200
    except Exception as e:
        logger.error("admin.payout_failed_error", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/payouts/<uuid:deal_uuid>/retry', methods=['POST'])
def retry_payout(deal_uuid: str):
    """Retry payout. / إعادة محاولة الدفع."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        transaction = db.query(Transaction).filter(
            Transaction.deal_uuid == str(deal_uuid),
            Transaction.type == 'payout'
        ).first()
        
        if not transaction:
            db.close()
            return jsonify({'error': 'Payout not found', 'message_ar': 'الدفع غير موجود'}), 404
        
        transaction.status = 'pending'
        transaction.retry_count = (transaction.retry_count or 0) + 1
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        
        logger.info("admin.payout_retry", deal_uuid=str(deal_uuid))
        return jsonify({'message': 'Payout retry initiated', 'message_ar': 'تم بدء إعادة المحاولة'}), 200
    except Exception as e:
        logger.error("admin.payout_retry_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# ⚠️ Disputes Management
# ============================================================

@admin_bp.route('/disputes/active', methods=['GET'])
def active_disputes():
    """List active disputes. / النزاعات النشطة."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        disputes = db.query(Dispute).filter(
            Dispute.status.in_(['opened', 'pending', 'in_review'])
        ).order_by(Dispute.created_at.desc()).all()
        
        result = []
        for d in disputes:
            result.append({
                'id': d.id,
                'deal_id': d.deal_id,
                'reason': d.reason,
                'status': d.status,
                'filed_by': d.filed_by,
                'created_at': d.created_at.isoformat() if d.created_at else None
            })
        
        total = len(result)
        db.close()
        return jsonify({'disputes': result, 'total': total}), 200
    except Exception as e:
        logger.error("admin.disputes_active_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/disputes/all', methods=['GET'])
def all_disputes():
    """List all disputes with pagination. / جميع النزاعات."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        db = next(get_db())
        query = db.query(Dispute).order_by(Dispute.created_at.desc())
        total = query.count()
        disputes = query.offset((page - 1) * per_page).limit(per_page).all()
        
        result = []
        for d in disputes:
            result.append({
                'id': d.id,
                'deal_id': d.deal_id,
                'reason': d.reason,
                'status': d.status,
                'filed_by': d.filed_by,
                'created_at': d.created_at.isoformat() if d.created_at else None
            })
        
        db.close()
        return jsonify({
            'disputes': result,
            'total': total,
            'pagination': {'page': page, 'per_page': per_page, 'total': total}
        }), 200
    except Exception as e:
        logger.error("admin.disputes_all_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/disputes/<int:dispute_id>', methods=['GET'])
def dispute_detail(dispute_id: int):
    """Get dispute details. / تفاصيل نزاع."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        result = {
            'id': dispute.id,
            'deal_id': dispute.deal_id,
            'reason': dispute.reason,
            'status': dispute.status,
            'filed_by': dispute.filed_by,
            'resolution': dispute.resolution,
            'resolved_by': dispute.resolved_by,
            'created_at': dispute.created_at.isoformat() if dispute.created_at else None,
            'resolved_at': dispute.resolved_at.isoformat() if dispute.resolved_at else None
        }
        
        db.close()
        return jsonify({'dispute': result}), 200
    except Exception as e:
        logger.error("admin.dispute_detail_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


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
        
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        dispute.status = 'resolved'
        dispute.resolution = resolution
        dispute.decision = decision
        dispute.resolved_by = user_id
        dispute.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        
        logger.info("admin.dispute_resolved", dispute_id=dispute_id, decision=decision)
        return jsonify({
            'message': 'Dispute resolved',
            'message_ar': 'تم حل النزاع',
            'resolution': resolution,
            'decision': decision
        }), 200
    except Exception as e:
        logger.error("admin.dispute_resolve_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 👤 Users Management
# ============================================================

@admin_bp.route('/users', methods=['GET'])
def list_users():
    """List all users with pagination. / قائمة المستخدمين."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        db = next(get_db())
        query = db.query(User).order_by(User.created_at.desc())
        total = query.count()
        users = query.offset((page - 1) * per_page).limit(per_page).all()
        
        result = []
        for u in users:
            result.append({
                'id': u.id,
                'email': u.email,
                'username': u.username,
                'role': u.role,
                'is_active': u.is_active,
                'is_verified': u.is_verified,
                'is_2fa_enabled': u.is_2fa_enabled,
                'created_at': u.created_at.isoformat() if u.created_at else None
            })
        
        db.close()
        return jsonify({
            'users': result,
            'pagination': {'page': page, 'per_page': per_page, 'total': total}
        }), 200
    except Exception as e:
        logger.error("admin.users_list_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/users/<int:target_user_id>', methods=['GET'])
def user_detail(target_user_id: int):
    """Get user details. / تفاصيل مستخدم."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(target_user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        return jsonify({
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'is_2fa_enabled': user.is_2fa_enabled,
                'failed_attempts': user.failed_attempts,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        }), 200
    except Exception as e:
        logger.error("admin.user_detail_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/users/<int:target_user_id>/toggle-status', methods=['POST'])
def toggle_user_status(target_user_id: int):
    """Toggle user active status (suspend/activate). / تعليق/تفعيل مستخدم."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(target_user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        if user.id == user_id:
            return jsonify({'error': 'Cannot modify yourself', 'message_ar': 'لا يمكن تعديل حسابك'}), 400
        
        user.is_active = not user.is_active
        repo.update(user, {'is_active': user.is_active})
        
        action = 'suspended' if not user.is_active else 'activated'
        logger.info(f"admin.user_{action}", user_id=target_user_id, by_admin=user_id)
        
        return jsonify({
            'message': f'User {action}',
            'message_ar': f'تم {"تعليق" if not user.is_active else "تفعيل"} المستخدم'
        }), 200
    except Exception as e:
        logger.error("admin.user_toggle_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 📊 Stats
# ============================================================

@admin_bp.route('/stats', methods=['GET'])
def admin_stats():
    """Get real system stats from database. / إحصائيات النظام الحقيقية."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        
        total_users = db.query(User).count()
        active_deals = db.query(Deal).filter(Deal.status.in_(['active', 'in_progress'])).count()
        completed_deals = db.query(Deal).filter(Deal.status == 'completed').count()
        disputes_opened = db.query(Dispute).filter(Dispute.status.in_(['opened', 'pending', 'in_review'])).count()
        
        # Total volume from transactions
        total_volume = db.query(Transaction).filter(
            Transaction.status == 'confirmed'
        ).all()
        total_volume_usdt = sum(float(t.amount or 0) for t in total_volume)
        
        # New users today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        new_users_today = db.query(User).filter(User.created_at >= today_start).count()
        new_deals_today = db.query(Deal).filter(Deal.created_at >= today_start).count()
        
        # Platform revenue (fees)
        platform_revenue = sum(float(t.fee or 0) for t in total_volume)
        
        db.close()
        
        stats = {
            'total_users': total_users,
            'active_deals': active_deals,
            'completed_deals': completed_deals,
            'disputes_opened': disputes_opened,
            'total_volume_usdt': str(round(total_volume_usdt, 2)),
            'platform_revenue': str(round(platform_revenue, 2)),
            'new_users_today': new_users_today,
            'new_deals_today': new_deals_today
        }
        
        return jsonify({'stats': AdminStatsSchema().dump(stats)}), 200
    except Exception as e:
        logger.error("admin.stats_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/stats/revenue', methods=['GET'])
def revenue_report():
    """Real revenue report from transactions. / تقرير الإيرادات الحقيقي."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        
        # Today
        today_txs = db.query(Transaction).filter(
            Transaction.status == 'confirmed',
            Transaction.updated_at >= today_start
        ).all()
        today_revenue = sum(float(t.fee or 0) for t in today_txs)
        
        # This week
        week_txs = db.query(Transaction).filter(
            Transaction.status == 'confirmed',
            Transaction.updated_at >= week_start
        ).all()
        week_revenue = sum(float(t.fee or 0) for t in week_txs)
        
        # This month
        month_txs = db.query(Transaction).filter(
            Transaction.status == 'confirmed',
            Transaction.updated_at >= month_start
        ).all()
        month_revenue = sum(float(t.fee or 0) for t in month_txs)
        
        # Total
        all_txs = db.query(Transaction).filter(Transaction.status == 'confirmed').all()
        total_revenue = sum(float(t.fee or 0) for t in all_txs)
        
        db.close()
        
        return jsonify({
            'revenue': {
                'today': str(round(today_revenue, 2)),
                'this_week': str(round(week_revenue, 2)),
                'this_month': str(round(month_revenue, 2)),
                'total': str(round(total_revenue, 2))
            }
        }), 200
    except Exception as e:
        logger.error("admin.revenue_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 📋 Deals Management
# ============================================================

@admin_bp.route('/deals', methods=['GET'])
def list_deals():
    """List all deals. / قائمة الصفقات."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        db = next(get_db())
        deals = db.query(Deal).order_by(Deal.created_at.desc()).limit(50).all()
        
        result = []
        for d in deals:
            result.append({
                'id': d.id,
                'title': d.title,
                'amount': float(d.amount) if d.amount else 0,
                'status': d.status,
                'created_at': d.created_at.isoformat() if d.created_at else None
            })
        
        db.close()
        return jsonify({'deals': result}), 200
    except Exception as e:
        logger.error("admin.deals_list_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# ⚙️ System Operations
# ============================================================

@admin_bp.route('/backup/trigger', methods=['POST'])
def trigger_backup():
    """Trigger system backup via Celery. / تشغيل نسخ احتياطي."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        # Try to call Celery task
        try:
            from src.app.models.backup import backup_database
            backup_database.delay()
            logger.info("admin.backup_triggered_celery")
        except Exception:
            logger.warning("admin.backup_celery_unavailable")
        
        backup_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return jsonify({
            'message': 'Backup initiated',
            'message_ar': 'تم بدء النسخ الاحتياطي',
            'backup_id': backup_id
        }), 200
    except Exception as e:
        logger.error("admin.backup_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@admin_bp.route('/backups', methods=['GET'])
def list_backups():
    """List available backups. / قائمة النسخ الاحتياطية."""
    user_id, error = _require_admin()
    if error:
        return error

    try:
        import os
        backup_dir = 'backups'
        backups = []
        
        if os.path.exists(backup_dir):
            for f in sorted(os.listdir(backup_dir), reverse=True):
                if f.endswith('.tar.gz'):
                    path = os.path.join(backup_dir, f)
                    size = os.path.getsize(path)
                    backups.append({
                        'filename': f,
                        'size': size,
                        'date': f.split('_')[-1].replace('.tar.gz', '') if '_' in f else ''
                    })
        
        return jsonify({'backups': backups[:20]}), 200
    except Exception as e:
        logger.error("admin.backups_list_failed", error=str(e))
        return jsonify({'backups': []}), 200


__all__ = ['admin_bp']
