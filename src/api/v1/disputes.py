"""
Disputes API Endpoints - SafeSend
نقاط نهاية النزاعات - SafeSend

Handles dispute creation, evidence management, messaging, and appeals.
يدير إنشاء النزاعات، إدارة الأدلة، المراسلة، والاستئناف.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog
import uuid

from src.app.models.database import get_db
from src.app.models.dispute import Dispute, DisputeStatus, DisputeReasonCategory
from src.app.models.deal import Deal
from src.app.models.message import Message, MessageType
from src.app.models.conversation import Conversation
from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import DisputeSchema

logger = structlog.get_logger(__name__)
disputes_bp = Blueprint('disputes_v1', __name__, url_prefix='/api/v1/disputes')

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
            return payload['user_id']
        except Exception:
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

# ============================================================
# ⚠️ Dispute Management - Real Database
# ============================================================

@disputes_bp.route('/open/<uuid:deal_uuid>', methods=['POST'])
def open_dispute(deal_uuid: str):
    """
    Open a dispute on a deal.
    فتح نزاع على صفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        reason_category = data.get('reason_category', DisputeReasonCategory.OTHER)
        
        if not reason:
            return jsonify({
                'error': 'Reason required',
                'message_ar': 'السبب مطلوب'
            }), 400
        
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()
        
        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        if str(deal.seller_id) != str(user_id) and str(deal.buyer_id) != str(user_id):
            db.close()
            return jsonify({
                'error': 'Not a participant in this deal',
                'message_ar': 'لست مشاركاً في هذه الصفقة'
            }), 403
        
        if deal.status not in ['funded', 'delivered']:
            db.close()
            return jsonify({
                'error': 'Deal not in disputable state',
                'message_ar': 'الصفقة ليست في حالة قابلة للنزاع'
            }), 400
        
        # Check for existing dispute
        existing = db.query(Dispute).filter(
            Dispute.deal_id == deal.uuid,
            Dispute.status.in_([DisputeStatus.OPENED, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_EVIDENCE])
        ).first()
        
        if existing:
            db.close()
            return jsonify({
                'error': 'Active dispute already exists',
                'message_ar': 'يوجد نزاع نشط مسبقاً',
                'dispute_id': str(existing.id)
            }), 409
        
        # Create dispute
        dispute = Dispute(
            deal_id=deal.uuid,
            opened_by_id=uuid.UUID(str(user_id).zfill(32)[:32]) if len(str(user_id)) < 32 else uuid.uuid4(),
            reason=reason,
            reason_category=reason_category,
            status=DisputeStatus.OPENED,
            evidence=[]
        )
        db.add(dispute)
        
        # Update deal status
        deal.status = 'disputed'
        
        db.commit()
        db.refresh(dispute)
        
        dispute_id = str(dispute.id)
        db.close()
        
        logger.info("dispute.opened", dispute_id=dispute_id, deal_uuid=str(deal_uuid))
        
        return jsonify({
            'message': 'Dispute opened',
            'message_ar': 'تم فتح النزاع',
            'dispute': {
                'id': dispute_id,
                'deal_id': str(deal_uuid),
                'opened_by_id': user_id,
                'reason': reason,
                'reason_category': reason_category,
                'status': DisputeStatus.OPENED,
                'evidence': [],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error("dispute.open_failed", error=str(e))
        return jsonify({
            'error': 'Failed to open dispute',
            'message_ar': 'فشل فتح النزاع'
        }), 500


@disputes_bp.route('/<dispute_id>/evidence', methods=['POST'])
def add_evidence(dispute_id: str):
    """Add evidence to a dispute in database. / إضافة دليل للنزاع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        description = data.get('description', '')
        file_ids = data.get('file_ids', [])
        
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == uuid.UUID(dispute_id)).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        if str(dispute.opened_by_id).replace('-', '') != str(user_id):
            db.close()
            return jsonify({'error': 'Only dispute opener can add evidence', 'message_ar': 'فقط فاتح النزاع يمكنه إضافة أدلة'}), 403
        
        if dispute.status not in [DisputeStatus.OPENED, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_EVIDENCE]:
            db.close()
            return jsonify({'error': 'Cannot add evidence in current status', 'message_ar': 'لا يمكن إضافة أدلة في الحالة الحالية'}), 400
        
        evidence_list = dispute.evidence or []
        new_evidence = {
            'id': len(evidence_list) + 1,
            'description': description,
            'file_ids': file_ids,
            'added_by': user_id,
            'added_at': datetime.now(timezone.utc).isoformat()
        }
        evidence_list.append(new_evidence)
        
        dispute.evidence = evidence_list
        dispute.status = DisputeStatus.AWAITING_EVIDENCE
        
        db.commit()
        db.close()
        
        logger.info("dispute.evidence_added", dispute_id=dispute_id)
        
        return jsonify({
            'message': 'Evidence added',
            'message_ar': 'تم إضافة الدليل',
            'evidence': new_evidence
        }), 200
        
    except Exception as e:
        logger.error("dispute.evidence_failed", error=str(e))
        return jsonify({'error': 'Failed to add evidence', 'message_ar': 'فشل إضافة الدليل'}), 500


@disputes_bp.route('/<dispute_id>', methods=['GET'])
def get_dispute(dispute_id: str):
    """Get dispute details from database. / تفاصيل النزاع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == uuid.UUID(dispute_id)).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        result = {
            'id': str(dispute.id),
            'deal_id': str(dispute.deal_id),
            'opened_by_id': str(dispute.opened_by_id),
            'reason': dispute.reason,
            'reason_category': dispute.reason_category,
            'status': dispute.status,
            'evidence': dispute.evidence or [],
            'resolution': dispute.resolution,
            'resolution_type': dispute.resolution_type,
            'created_at': dispute.created_at.isoformat() if dispute.created_at else None,
            'resolved_at': dispute.resolved_at.isoformat() if dispute.resolved_at else None
        }
        
        db.close()
        return jsonify({'dispute': result}), 200
        
    except Exception as e:
        logger.error("dispute.get_failed", error=str(e))
        return jsonify({'error': 'Failed to fetch dispute', 'message_ar': 'فشل جلب النزاع'}), 500


@disputes_bp.route('/my-disputes', methods=['GET'])
def my_disputes():
    """List user disputes from database. / قائمة نزاعات المستخدم."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        
        # Query using string matching for UUID
        disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
        
        # Filter by user_id (since UUID comparison is tricky)
        user_disputes = []
        for d in disputes:
            try:
                if str(d.opened_by_id).replace('-', '') == str(user_id):
                    user_disputes.append({
                        'id': str(d.id),
                        'deal_id': str(d.deal_id),
                        'reason': d.reason,
                        'status': d.status,
                        'created_at': d.created_at.isoformat() if d.created_at else None
                    })
            except Exception:
                continue
        
        db.close()
        return jsonify({'disputes': user_disputes}), 200
        
    except Exception as e:
        logger.error("dispute.list_failed", error=str(e))
        return jsonify({'error': 'Failed to list disputes', 'message_ar': 'فشل جلب النزاعات'}), 500


@disputes_bp.route('/<dispute_id>/appeal', methods=['POST'])
def appeal_dispute(dispute_id: str):
    """Appeal a dispute decision in database. / استئناف قرار النزاع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == uuid.UUID(dispute_id)).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        if str(dispute.opened_by_id).replace('-', '') != str(user_id):
            db.close()
            return jsonify({'error': 'Only dispute opener can appeal', 'message_ar': 'فقط فاتح النزاع يمكنه الاستئناف'}), 403
        
        if dispute.status not in ['resolved_buyer', 'resolved_seller', 'resolved_split']:
            db.close()
            return jsonify({'error': 'Dispute not yet resolved', 'message_ar': 'النزاع لم يحل بعد'}), 400
        
        if dispute.appeal_reason:
            db.close()
            return jsonify({'error': 'Already appealed', 'message_ar': 'تم الاستئناف مسبقاً'}), 400
        
        dispute.status = 'appealed'
        dispute.appeal_reason = reason
        
        db.commit()
        db.close()
        
        logger.info("dispute.appealed", dispute_id=dispute_id)
        return jsonify({'message': 'Appeal submitted', 'message_ar': 'تم تقديم الاستئناف'}), 200
        
    except Exception as e:
        logger.error("dispute.appeal_failed", error=str(e))
        return jsonify({'error': 'Appeal failed', 'message_ar': 'فشل الاستئناف'}), 500


@disputes_bp.route('/<dispute_id>/timeline', methods=['GET'])
def dispute_timeline(dispute_id: str):
    """Get dispute timeline from database. / الجدول الزمني للنزاع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        dispute = db.query(Dispute).filter(Dispute.id == uuid.UUID(dispute_id)).first()
        
        if not dispute:
            db.close()
            return jsonify({'error': 'Dispute not found', 'message_ar': 'النزاع غير موجود'}), 404
        
        timeline = [{
            'event': 'dispute_opened',
            'timestamp': dispute.created_at.isoformat() if dispute.created_at else None,
            'description': 'تم فتح النزاع'
        }]
        
        for evidence in (dispute.evidence or []):
            timeline.append({
                'event': 'evidence_added',
                'timestamp': evidence.get('added_at'),
                'description': evidence.get('description', '')
            })
        
        if dispute.resolved_at:
            timeline.append({
                'event': 'dispute_resolved',
                'timestamp': dispute.resolved_at.isoformat(),
                'description': f"النتيجة: {dispute.resolution_type or dispute.resolution or ''}"
            })
        
        if dispute.appeal_reason:
            timeline.append({
                'event': 'dispute_appealed',
                'timestamp': dispute.updated_at.isoformat() if dispute.updated_at else None,
                'description': dispute.appeal_reason
            })
        
        db.close()
        return jsonify({'dispute_id': dispute_id, 'timeline': timeline}), 200
        
    except Exception as e:
        logger.error("dispute.timeline_failed", error=str(e))
        return jsonify({'error': 'Failed to fetch timeline', 'message_ar': 'فشل جلب الجدول الزمني'}), 500


__all__ = ['disputes_bp']
