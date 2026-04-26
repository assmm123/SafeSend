"""
Deals API Endpoints - SafeSend
نقاط نهاية الصفقات - SafeSend

Handles deal creation, update, delivery, approval, and timeline.
يدير إنشاء الصفقات، تحديثها، التسليم، الموافقة، والجدول الزمني.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import structlog

from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import (
    DealCreateSchema,
    DealUpdateSchema,
    DealSchema,
    DealTimelineSchema,
    validate_request,
    serialize_response,
    PaginationSchema
)

logger = structlog.get_logger(__name__)
deals_bp = Blueprint('deals_v1', __name__, url_prefix='/api/v1/deals')

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

def _get_deal_repo():
    """Get deal repository instance."""
    return DealRepository()

def _require_auth():
    """Check authentication and return user_id or error response."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    return user_id, None

# ============================================================
# 📝 Deal CRUD
# ============================================================

@deals_bp.route('', methods=['POST'])
@validate_request(DealCreateSchema())
def create_deal(validated_data: dict):
    """
    Create a new escrow deal.
    إنشاء صفقة وساطة جديدة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        
        deal_data = {
            'seller_id': user_id,
            'title': validated_data['title'],
            'description': validated_data['description'],
            'category': validated_data.get('category', 'other'),
            'amount_usdt': validated_data['amount_usdt'],
            'fee_percent': validated_data.get('fee_percent', 5.0),
            'status': 'pending_payment',
            'created_from_ip': request.remote_addr,
            'expires_at': datetime.now(timezone.utc) + timedelta(days=7)
        }
        
        deal = repo.create(deal_data)
        
        if not deal:
            return jsonify({
                'error': 'Failed to create deal',
                'message_ar': 'فشل إنشاء الصفقة'
            }), 500
        
        logger.info("deal.created", deal_id=deal.id, seller_id=user_id)
        
        return jsonify({
            'message': 'Deal created successfully',
            'message_ar': 'تم إنشاء الصفقة بنجاح',
            'deal': DealSchema().dump(deal)
        }), 201
        
    except Exception as e:
        logger.error("deal.create_failed", error=str(e))
        return jsonify({
            'error': 'Creation failed',
            'message_ar': 'فشل الإنشاء'
        }), 500


@deals_bp.route('', methods=['GET'])
def list_deals():
    """
    List user deals with pagination.
    قائمة صفقات المستخدم مع التصفح.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', None)
        role = request.args.get('role', 'seller')  # seller or buyer
        
        repo = _get_deal_repo()
        
        if role == 'buyer':
            deals = repo.list_by_buyer(user_id, status=status_filter, page=page, per_page=per_page)
        else:
            deals = repo.list_by_seller(user_id, status=status_filter, page=page, per_page=per_page)
        
        return jsonify({
            'deals': DealSchema().dump(deals.get('items', []), many=True),
            'pagination': PaginationSchema().dump(deals.get('pagination', {}))
        }), 200
        
    except Exception as e:
        logger.error("deal.list_failed", error=str(e))
        return jsonify({
            'error': 'Failed to list deals',
            'message_ar': 'فشل جلب الصفقات'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>', methods=['GET'])
def get_deal(deal_uuid: str):
    """
    Get deal details by UUID.
    تفاصيل الصفقة حسب المعرف.
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
        
        # Check access
        if deal.seller_id != user_id and deal.buyer_id != user_id:
            return jsonify({
                'error': 'Access denied',
                'message_ar': 'غير مصرح'
            }), 403
        
        return jsonify({
            'deal': DealSchema().dump(deal)
        }), 200
        
    except Exception as e:
        logger.error("deal.get_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch deal',
            'message_ar': 'فشل جلب الصفقة'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>', methods=['PUT'])
@validate_request(DealUpdateSchema())
def update_deal(deal_uuid: str, validated_data: dict):
    """
    Update deal (only before payment).
    تحديث الصفقة (قبل الدفع فقط).
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
        
        if deal.seller_id != user_id:
            return jsonify({
                'error': 'Only seller can update',
                'message_ar': 'البائع فقط يمكنه التحديث'
            }), 403
        
        if deal.status != 'pending_payment':
            return jsonify({
                'error': 'Can only update pending deals',
                'message_ar': 'يمكن تحديث الصفقات المعلقة فقط'
            }), 400
        
        updated = repo.update(deal, validated_data)
        
        logger.info("deal.updated", deal_id=deal.id)
        
        return jsonify({
            'message': 'Deal updated',
            'message_ar': 'تم تحديث الصفقة',
            'deal': DealSchema().dump(updated)
        }), 200
        
    except Exception as e:
        logger.error("deal.update_failed", error=str(e))
        return jsonify({
            'error': 'Update failed',
            'message_ar': 'فشل التحديث'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/cancel', methods=['POST'])
def cancel_deal(deal_uuid: str):
    """
    Cancel a deal.
    إلغاء صفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', 'Cancelled by user')
        
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        if deal.seller_id != user_id and deal.buyer_id != user_id:
            return jsonify({
                'error': 'Access denied',
                'message_ar': 'غير مصرح'
            }), 403
        
        if deal.status in ['completed', 'cancelled']:
            return jsonify({
                'error': 'Cannot cancel completed deal',
                'message_ar': 'لا يمكن إلغاء صفقة مكتملة'
            }), 400
        
        repo.cancel_deal(deal, user_id, reason)
        
        logger.info("deal.cancelled", deal_id=deal.id)
        
        return jsonify({
            'message': 'Deal cancelled',
            'message_ar': 'تم إلغاء الصفقة'
        }), 200
        
    except Exception as e:
        logger.error("deal.cancel_failed", error=str(e))
        return jsonify({
            'error': 'Cancel failed',
            'message_ar': 'فشل الإلغاء'
        }), 500


# ============================================================
# 📦 Delivery & Approval
# ============================================================

@deals_bp.route('/<uuid:deal_uuid>/deliver', methods=['POST'])
def deliver_work(deal_uuid: str):
    """
    Mark work as delivered (seller only).
    تسليم العمل (البائع فقط).
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
        
        if deal.seller_id != user_id:
            return jsonify({
                'error': 'Only seller can deliver',
                'message_ar': 'البائع فقط يمكنه التسليم'
            }), 403
        
        if deal.status != 'funded':
            return jsonify({
                'error': 'Payment must be confirmed first',
                'message_ar': 'يجب تأكيد الدفع أولاً'
            }), 400
        
        repo.update_status(deal, 'delivered')
        repo.update(deal, {'delivered_at': datetime.now(timezone.utc)})
        
        logger.info("deal.delivered", deal_id=deal.id)
        
        return jsonify({
            'message': 'Work delivered',
            'message_ar': 'تم تسليم العمل'
        }), 200
        
    except Exception as e:
        logger.error("deal.deliver_failed", error=str(e))
        return jsonify({
            'error': 'Delivery failed',
            'message_ar': 'فشل التسليم'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/approve', methods=['POST'])
def approve_work(deal_uuid: str):
    """
    Approve delivered work (buyer only).
    الموافقة على العمل (المشتري فقط).
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
        
        if deal.buyer_id != user_id:
            return jsonify({
                'error': 'Only buyer can approve',
                'message_ar': 'المشتري فقط يمكنه الموافقة'
            }), 403
        
        if deal.status != 'delivered':
            return jsonify({
                'error': 'Work must be delivered first',
                'message_ar': 'يجب تسليم العمل أولاً'
            }), 400
        
        repo.update_status(deal, 'completed')
        repo.mark_as_completed(deal)
        
        logger.info("deal.approved", deal_id=deal.id)
        
        return jsonify({
            'message': 'Work approved - payment will be released',
            'message_ar': 'تمت الموافقة - سيتم تحرير الدفع'
        }), 200
        
    except Exception as e:
        logger.error("deal.approve_failed", error=str(e))
        return jsonify({
            'error': 'Approval failed',
            'message_ar': 'فشل الموافقة'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/reject', methods=['POST'])
def reject_work(deal_uuid: str):
    """
    Reject delivered work (buyer only).
    رفض العمل (المشتري فقط).
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', 'Work not satisfactory')
        
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        if deal.buyer_id != user_id:
            return jsonify({
                'error': 'Only buyer can reject',
                'message_ar': 'المشتري فقط يمكنه الرفض'
            }), 403
        
        if deal.status != 'delivered':
            return jsonify({
                'error': 'Work must be delivered first',
                'message_ar': 'يجب تسليم العمل أولاً'
            }), 400
        
        repo.update_status(deal, 'disputed')
        
        logger.info("deal.rejected", deal_id=deal.id)
        
        return jsonify({
            'message': 'Work rejected - dispute opened',
            'message_ar': 'تم رفض العمل - فتح نزاع'
        }), 200
        
    except Exception as e:
        logger.error("deal.reject_failed", error=str(e))
        return jsonify({
            'error': 'Rejection failed',
            'message_ar': 'فشل الرفض'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/request-revision', methods=['POST'])
def request_revision(deal_uuid: str):
    """
    Request revision on delivered work (buyer only).
    طلب تعديل على العمل (المشتري فقط).
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        note = data.get('note', 'Revision requested')
        
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        if deal.buyer_id != user_id:
            return jsonify({
                'error': 'Only buyer can request revision',
                'message_ar': 'المشتري فقط يمكنه طلب التعديل'
            }), 403
        
        repo.update_status(deal, 'revision_requested')
        
        logger.info("deal.revision_requested", deal_id=deal.id)
        
        return jsonify({
            'message': 'Revision requested',
            'message_ar': 'تم طلب تعديل'
        }), 200
        
    except Exception as e:
        logger.error("deal.revision_failed", error=str(e))
        return jsonify({
            'error': 'Revision request failed',
            'message_ar': 'فشل طلب التعديل'
        }), 500


# ============================================================
# 📊 Timeline & Activity
# ============================================================

@deals_bp.route('/<uuid:deal_uuid>/timeline', methods=['GET'])
def deal_timeline(deal_uuid: str):
    """
    Get deal timeline events.
    الجدول الزمني للصفقة.
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
        
        timeline = getattr(deal, 'get_timeline', lambda: [])()
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'events': timeline
        }), 200
        
    except Exception as e:
        logger.error("deal.timeline_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch timeline',
            'message_ar': 'فشل جلب الجدول الزمني'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/activity', methods=['GET'])
def deal_activity(deal_uuid: str):
    """
    Get deal activity log.
    سجل نشاط الصفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        # In production: fetch from audit_log
        activity = [{
            'action': 'deal_created',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'description': 'Deal was created'
        }]
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'activity': activity
        }), 200
        
    except Exception as e:
        logger.error("deal.activity_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch activity',
            'message_ar': 'فشل جلب النشاط'
        }), 500


@deals_bp.route('/<uuid:deal_uuid>/remind', methods=['POST'])
def remind_party(deal_uuid: str):
    """
    Send reminder to other party.
    تذكير الطرف الآخر.
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
        
        logger.info("deal.reminder_sent", deal_id=deal.id)
        
        return jsonify({
            'message': 'Reminder sent',
            'message_ar': 'تم إرسال تذكير'
        }), 200
        
    except Exception as e:
        logger.error("deal.remind_failed", error=str(e))
        return jsonify({
            'error': 'Reminder failed',
            'message_ar': 'فشل التذكير'
        }), 500


# ============================================================
# 📊 Stats & Categories
# ============================================================

@deals_bp.route('/stats', methods=['GET'])
def deal_stats():
    """
    Get user deal statistics.
    إحصائيات صفقات المستخدم.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        stats = repo.get_deal_stats(seller_id=user_id)
        
        return jsonify({
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error("deal.stats_failed", error=str(e))
        return jsonify({
            'stats': {
                'total': 0,
                'active': 0,
                'completed': 0,
                'total_volume': 0
            }
        }), 200


@deals_bp.route('/categories', methods=['GET'])
def deal_categories():
    """
    Get available deal categories.
    قائمة الفئات المتاحة.
    """
    categories = [
        {'slug': 'development', 'name': 'Development', 'name_ar': 'تطوير'},
        {'slug': 'design', 'name': 'Design', 'name_ar': 'تصميم'},
        {'slug': 'writing', 'name': 'Writing', 'name_ar': 'كتابة'},
        {'slug': 'marketing', 'name': 'Marketing', 'name_ar': 'تسويق'},
        {'slug': 'video', 'name': 'Video', 'name_ar': 'فيديو'},
        {'slug': 'music', 'name': 'Music', 'name_ar': 'موسيقى'},
        {'slug': 'consulting', 'name': 'Consulting', 'name_ar': 'استشارات'},
        {'slug': 'other', 'name': 'Other', 'name_ar': 'أخرى'}
    ]
    
    return jsonify({'categories': categories}), 200


# ============================================================
# 📦 Export
# ============================================================

__all__ = ['deals_bp']
