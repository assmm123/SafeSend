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

from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import (
    DisputeCreateSchema,
    DisputeEvidenceSchema,
    DisputeSchema,
    validate_request
)

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

# Temporary in-memory dispute store
_disputes = {}
_dispute_messages = {}
_dispute_counter = 0

# ============================================================
# ⚠️ Dispute Management
# ============================================================

@disputes_bp.route('/open/<uuid:deal_uuid>', methods=['POST'])
@validate_request(DisputeCreateSchema())
def open_dispute(deal_uuid: str, validated_data: dict):
    """
    Open a dispute on a deal.
    فتح نزاع على صفقة.
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
        
        if deal.seller_id != user_id and deal.buyer_id != user_id:
            return jsonify({
                'error': 'Not a participant in this deal',
                'message_ar': 'لست مشاركاً في هذه الصفقة'
            }), 403
        
        if deal.status not in ['funded', 'delivered']:
            return jsonify({
                'error': 'Deal not in disputable state',
                'message_ar': 'الصفقة ليست في حالة قابلة للنزاع'
            }), 400
        
        global _dispute_counter
        _dispute_counter += 1
        dispute_id = _dispute_counter
        
        dispute = {
            'id': dispute_id,
            'dispute_uuid': str(deal_uuid),
            'deal_id': deal.id,
            'opened_by_id': user_id,
            'reason': validated_data['reason'],
            'reason_category': validated_data['reason_category'],
            'evidence': [],
            'status': 'opened',
            'resolution': None,
            'resolved_by_id': None,
            'resolved_at': None,
            'appealed_at': None,
            'appeal_reason': None,
            'created_at': datetime.now(timezone.utc)
        }
        
        _disputes[dispute_id] = dispute
        _dispute_messages[dispute_id] = []
        
        # Update deal status
        repo.update_status(deal, 'disputed')
        
        logger.info("dispute.opened", dispute_id=dispute_id, deal_id=deal.id)
        
        return jsonify({
            'message': 'Dispute opened',
            'message_ar': 'تم فتح النزاع',
            'dispute': DisputeSchema().dump(dispute)
        }), 201
        
    except Exception as e:
        logger.error("dispute.open_failed", error=str(e))
        return jsonify({
            'error': 'Failed to open dispute',
            'message_ar': 'فشل فتح النزاع'
        }), 500


@disputes_bp.route('/<int:dispute_id>/evidence', methods=['POST'])
@validate_request(DisputeEvidenceSchema())
def add_evidence(dispute_id: int, validated_data: dict):
    """
    Add evidence to a dispute.
    إضافة دليل للنزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        if dispute['opened_by_id'] != user_id:
            return jsonify({
                'error': 'Only dispute opener can add evidence',
                'message_ar': 'فقط فاتح النزاع يمكنه إضافة أدلة'
            }), 403
        
        if dispute['status'] not in ['opened', 'under_review', 'awaiting_evidence']:
            return jsonify({
                'error': 'Cannot add evidence in current status',
                'message_ar': 'لا يمكن إضافة أدلة في الحالة الحالية'
            }), 400
        
        evidence = {
            'id': len(dispute['evidence']) + 1,
            'description': validated_data['description'],
            'file_ids': validated_data['file_ids'],
            'added_at': datetime.now(timezone.utc).isoformat(),
            'added_by': user_id
        }
        
        dispute['evidence'].append(evidence)
        dispute['status'] = 'awaiting_evidence'
        
        logger.info("dispute.evidence_added", dispute_id=dispute_id)
        
        return jsonify({
            'message': 'Evidence added',
            'message_ar': 'تم إضافة الدليل',
            'evidence': evidence
        }), 200
        
    except Exception as e:
        logger.error("dispute.evidence_failed", error=str(e))
        return jsonify({
            'error': 'Failed to add evidence',
            'message_ar': 'فشل إضافة الدليل'
        }), 500


@disputes_bp.route('/<int:dispute_id>/evidence/<int:evidence_index>', methods=['DELETE'])
def remove_evidence(dispute_id: int, evidence_index: int):
    """
    Remove evidence from a dispute.
    حذف دليل من النزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        if dispute['opened_by_id'] != user_id:
            return jsonify({
                'error': 'Only dispute opener can remove evidence',
                'message_ar': 'فقط فاتح النزاع يمكنه حذف الأدلة'
            }), 403
        
        if evidence_index < 0 or evidence_index >= len(dispute['evidence']):
            return jsonify({
                'error': 'Evidence not found',
                'message_ar': 'الدليل غير موجود'
            }), 404
        
        removed = dispute['evidence'].pop(evidence_index)
        
        logger.info("dispute.evidence_removed", dispute_id=dispute_id, index=evidence_index)
        
        return jsonify({
            'message': 'Evidence removed',
            'message_ar': 'تم حذف الدليل'
        }), 200
        
    except Exception as e:
        logger.error("dispute.evidence_remove_failed", error=str(e))
        return jsonify({
            'error': 'Failed to remove evidence',
            'message_ar': 'فشل حذف الدليل'
        }), 500


@disputes_bp.route('/<int:dispute_id>', methods=['GET'])
def get_dispute(dispute_id: int):
    """
    Get dispute details.
    تفاصيل النزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        return jsonify({
            'dispute': DisputeSchema().dump(dispute)
        }), 200
        
    except Exception as e:
        logger.error("dispute.get_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch dispute',
            'message_ar': 'فشل جلب النزاع'
        }), 500


@disputes_bp.route('/my-disputes', methods=['GET'])
def my_disputes():
    """
    List user disputes.
    قائمة نزاعات المستخدم.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        user_disputes = [
            d for d in _disputes.values()
            if d['opened_by_id'] == user_id
        ]
        
        return jsonify({
            'disputes': DisputeSchema().dump(user_disputes, many=True)
        }), 200
        
    except Exception as e:
        logger.error("dispute.list_failed", error=str(e))
        return jsonify({
            'error': 'Failed to list disputes',
            'message_ar': 'فشل جلب النزاعات'
        }), 500


@disputes_bp.route('/<int:dispute_id>/message', methods=['POST'])
def send_dispute_message(dispute_id: int):
    """
    Send message to mediator.
    إرسال رسالة للوسيط.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        
        if not content:
            return jsonify({
                'error': 'Message content required',
                'message_ar': 'محتوى الرسالة مطلوب'
            }), 400
        
        message = {
            'id': len(_dispute_messages.get(dispute_id, [])) + 1,
            'sender_id': user_id,
            'content': content,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        if dispute_id not in _dispute_messages:
            _dispute_messages[dispute_id] = []
        _dispute_messages[dispute_id].append(message)
        
        logger.info("dispute.message_sent", dispute_id=dispute_id)
        
        return jsonify({
            'message': 'Message sent',
            'message_ar': 'تم إرسال الرسالة',
            'data': message
        }), 200
        
    except Exception as e:
        logger.error("dispute.message_failed", error=str(e))
        return jsonify({
            'error': 'Failed to send message',
            'message_ar': 'فشل إرسال الرسالة'
        }), 500


@disputes_bp.route('/<int:dispute_id>/messages', methods=['GET'])
def dispute_messages(dispute_id: int):
    """
    Get dispute messages.
    محادثة النزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        messages = _dispute_messages.get(dispute_id, [])
        
        return jsonify({
            'dispute_id': dispute_id,
            'messages': messages
        }), 200
        
    except Exception as e:
        logger.error("dispute.messages_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch messages',
            'message_ar': 'فشل جلب الرسائل'
        }), 500


@disputes_bp.route('/<int:dispute_id>/appeal', methods=['POST'])
def appeal_dispute(dispute_id: int):
    """
    Appeal a dispute decision.
    استئناف قرار النزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        if dispute['opened_by_id'] != user_id:
            return jsonify({
                'error': 'Only dispute opener can appeal',
                'message_ar': 'فقط فاتح النزاع يمكنه الاستئناف'
            }), 403
        
        if dispute['status'] not in ['resolved_buyer', 'resolved_seller', 'resolved_split']:
            return jsonify({
                'error': 'Dispute not yet resolved',
                'message_ar': 'النزاع لم يحل بعد'
            }), 400
        
        if dispute.get('appealed_at'):
            return jsonify({
                'error': 'Already appealed',
                'message_ar': 'تم الاستئناف مسبقاً'
            }), 400
        
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        
        dispute['status'] = 'appealed'
        dispute['appealed_at'] = datetime.now(timezone.utc)
        dispute['appeal_reason'] = reason
        
        logger.info("dispute.appealed", dispute_id=dispute_id)
        
        return jsonify({
            'message': 'Appeal submitted',
            'message_ar': 'تم تقديم الاستئناف'
        }), 200
        
    except Exception as e:
        logger.error("dispute.appeal_failed", error=str(e))
        return jsonify({
            'error': 'Appeal failed',
            'message_ar': 'فشل الاستئناف'
        }), 500


@disputes_bp.route('/<int:dispute_id>/timeline', methods=['GET'])
def dispute_timeline(dispute_id: int):
    """
    Get dispute timeline.
    الجدول الزمني للنزاع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        dispute = _disputes.get(dispute_id)
        if not dispute:
            return jsonify({
                'error': 'Dispute not found',
                'message_ar': 'النزاع غير موجود'
            }), 404
        
        timeline = [
            {
                'event': 'dispute_opened',
                'timestamp': dispute['created_at'].isoformat(),
                'description': 'Dispute was opened'
            }
        ]
        
        for evidence in dispute.get('evidence', []):
            timeline.append({
                'event': 'evidence_added',
                'timestamp': evidence['added_at'],
                'description': evidence['description']
            })
        
        if dispute.get('resolved_at'):
            timeline.append({
                'event': 'dispute_resolved',
                'timestamp': dispute['resolved_at'].isoformat(),
                'description': f"Resolution: {dispute.get('resolution', '')}"
            })
        
        if dispute.get('appealed_at'):
            timeline.append({
                'event': 'dispute_appealed',
                'timestamp': dispute['appealed_at'].isoformat(),
                'description': dispute.get('appeal_reason', '')
            })
        
        return jsonify({
            'dispute_id': dispute_id,
            'timeline': timeline
        }), 200
        
    except Exception as e:
        logger.error("dispute.timeline_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch timeline',
            'message_ar': 'فشل جلب الجدول الزمني'
        }), 500


# ============================================================
# 📦 Export
# ============================================================

__all__ = ['disputes_bp']
