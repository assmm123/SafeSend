"""
Dispute Resolution Service - SafeSend
خدمة حل النزاعات - SafeSend

Manages dispute lifecycle: creation, mediator assignment, evidence, resolution, and appeal.
يدير دورة حياة النزاع: الإنشاء، تعيين الوسيط، الأدلة، الحل، والاستئناف.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)

DISPUTE_STATUSES = ['opened', 'under_review', 'awaiting_evidence', 'mediation', 
                    'resolved_buyer', 'resolved_seller', 'resolved_split', 'closed', 'appealed']
RESPONSE_DEADLINE_HOURS = 48
APPEAL_DEADLINE_DAYS = 7
MAX_APPEALS = 1

class DisputeResolution:
    """
    Dispute resolution and mediation service.
    خدمة حل النزاعات والوساطة.
    """
    
    def __init__(self):
        self._disputes: Dict[int, Dict[str, Any]] = {}
        self._mediators: List[Dict[str, Any]] = [
            {'id': 1, 'name': 'Admin 1', 'expertise': ['quality', 'delivery'], 'active_disputes': 0},
            {'id': 2, 'name': 'Admin 2', 'expertise': ['communication', 'payment'], 'active_disputes': 0},
        ]
        self._dispute_counter = 0
    
    # ============================================================
    # Dispute Creation
    # ============================================================
    
    def create_dispute(self, deal_id: int, opened_by: int, against: int, 
                       reason: str, category: str, evidence: List[Dict] = None) -> Dict[str, Any]:
        """
        Create a new dispute.
        إنشاء نزاع جديد.
        """
        valid_categories = ['quality', 'delivery', 'communication', 'payment']
        if category not in valid_categories:
            return {'success': False, 'error': 'invalid_category', 
                    'message': f'فئة غير صالحة: {category}'}
        
        self._dispute_counter += 1
        dispute_id = self._dispute_counter
        
        dispute = {
            'id': dispute_id,
            'deal_id': deal_id,
            'opened_by': opened_by,
            'against': against,
            'reason': reason,
            'category': category,
            'status': 'opened',
            'evidence': evidence or [],
            'mediator_id': None,
            'resolution': None,
            'resolution_type': None,
            'resolved_at': None,
            'appeal_count': 0,
            'appeal_reason': None,
            'deadline': datetime.now(timezone.utc) + timedelta(hours=RESPONSE_DEADLINE_HOURS),
            'timeline': [{
                'event': 'dispute_opened',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': f'Opened by user {opened_by}: {reason[:50]}'
            }],
            'created_at': datetime.now(timezone.utc)
        }
        
        self._disputes[dispute_id] = dispute
        logger.info("dispute.created", dispute_id=dispute_id, deal_id=deal_id, category=category)
        
        return {'success': True, 'message': 'تم فتح النزاع', 'dispute': dispute}
    
    # ============================================================
    # Evidence Management
    # ============================================================
    
    def add_evidence(self, dispute_id: int, evidence: Dict[str, Any], added_by: int) -> Dict[str, Any]:
        """
        Add evidence to dispute with timestamp.
        إضافة دليل مع توقيع زمني.
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        if dispute['status'] in ['resolved_buyer', 'resolved_seller', 'resolved_split', 'closed']:
            return {'success': False, 'error': 'already_resolved', 'message': 'النزاع محلول مسبقاً'}
        
        evidence['added_by'] = added_by
        evidence['added_at'] = datetime.now(timezone.utc).isoformat()
        evidence['id'] = len(dispute['evidence']) + 1
        
        dispute['evidence'].append(evidence)
        dispute['timeline'].append({
            'event': 'evidence_added',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Evidence #{evidence["id"]} added by {added_by}'
        })
        
        logger.info("dispute.evidence_added", dispute_id=dispute_id)
        return {'success': True, 'message': 'تم إضافة الدليل', 'evidence': evidence}
    
    # ============================================================
    # Mediator Assignment
    # ============================================================
    
    def assign_mediator(self, dispute_id: int, mediator_id: int = None) -> Dict[str, Any]:
        """
        Assign a mediator to dispute (auto or manual).
        تعيين وسيط للنزاع (تلقائي أو يدوي).
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        # Auto-assign based on expertise
        if not mediator_id:
            category = dispute.get('category', 'quality')
            available = [m for m in self._mediators 
                        if category in m['expertise'] and m['active_disputes'] < 5]
            if available:
                mediator = available[0]
                mediator_id = mediator['id']
                mediator['active_disputes'] += 1
            else:
                # Fallback to first mediator
                mediator = self._mediators[0]
                mediator_id = mediator['id']
                mediator['active_disputes'] += 1
        
        dispute['mediator_id'] = mediator_id
        dispute['status'] = 'under_review'
        dispute['timeline'].append({
            'event': 'mediator_assigned',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Mediator #{mediator_id} assigned'
        })
        
        logger.info("dispute.mediator_assigned", dispute_id=dispute_id, mediator_id=mediator_id)
        return {'success': True, 'message': 'تم تعيين الوسيط', 'mediator_id': mediator_id}
    
    # ============================================================
    # Resolution
    # ============================================================
    
    def resolve_dispute(self, dispute_id: int, resolved_by: int, 
                        decision: str, notes: str = '') -> Dict[str, Any]:
        """
        Resolve dispute with decision.
        حل النزاع بقرار.
        
        Decision types: refund_buyer, pay_seller, split_5050, split_custom, custom_split_percent
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        if dispute['status'] in ['resolved_buyer', 'resolved_seller', 'resolved_split', 'closed']:
            return {'success': False, 'error': 'already_resolved'}
        
        valid_decisions = ['refund_buyer', 'pay_seller', 'split_5050', 'split_custom']
        if decision not in valid_decisions:
            return {'success': False, 'error': 'invalid_decision'}
        
        # Map decision to status
        status_map = {
            'refund_buyer': 'resolved_buyer',
            'pay_seller': 'resolved_seller',
            'split_5050': 'resolved_split',
            'split_custom': 'resolved_split'
        }
        
        dispute['status'] = status_map[decision]
        dispute['resolution'] = decision
        dispute['resolution_type'] = decision
        dispute['resolved_by'] = resolved_by
        dispute['resolved_at'] = datetime.now(timezone.utc)
        dispute['resolution_notes'] = notes
        dispute['timeline'].append({
            'event': 'resolved',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Decision: {decision} by {resolved_by}'
        })
        
        # Release mediator
        if dispute.get('mediator_id'):
            for m in self._mediators:
                if m['id'] == dispute['mediator_id']:
                    m['active_disputes'] = max(0, m['active_disputes'] - 1)
        
        logger.info("dispute.resolved", dispute_id=dispute_id, decision=decision)
        return {'success': True, 'message': 'تم حل النزاع', 'decision': decision}
    
    # ============================================================
    # Appeal
    # ============================================================
    
    def appeal_decision(self, dispute_id: int, appealed_by: int, reason: str) -> Dict[str, Any]:
        """
        Appeal a dispute decision.
        استئناف قرار النزاع.
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        if dispute['status'] not in ['resolved_buyer', 'resolved_seller', 'resolved_split']:
            return {'success': False, 'error': 'not_resolved', 'message': 'النزاع لم يحل بعد'}
        
        if dispute['appeal_count'] >= MAX_APPEALS:
            return {'success': False, 'error': 'max_appeals', 'message': 'تم استخدام الحد الأقصى للاستئناف'}
        
        resolved_at = dispute['resolved_at']
        if resolved_at and datetime.now(timezone.utc) > resolved_at + timedelta(days=APPEAL_DEADLINE_DAYS):
            return {'success': False, 'error': 'appeal_deadline_passed', 'message': 'انتهت مهلة الاستئناف'}
        
        dispute['status'] = 'appealed'
        dispute['appeal_count'] += 1
        dispute['appeal_reason'] = reason
        dispute['appealed_by'] = appealed_by
        dispute['appealed_at'] = datetime.now(timezone.utc)
        dispute['timeline'].append({
            'event': 'appealed',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Appeal #{dispute["appeal_count"]} by {appealed_by}: {reason[:50]}'
        })
        
        logger.info("dispute.appealed", dispute_id=dispute_id, appeal_count=dispute['appeal_count'])
        return {'success': True, 'message': 'تم تقديم الاستئناف'}
    
    # ============================================================
    # Queries
    # ============================================================
    
    def get_dispute(self, dispute_id: int) -> Optional[Dict[str, Any]]:
        """Get dispute details. / تفاصيل النزاع."""
        return self._disputes.get(dispute_id)
    
    def get_dispute_timeline(self, dispute_id: int) -> List[Dict[str, Any]]:
        """Get dispute timeline. / الجدول الزمني للنزاع."""
        dispute = self._disputes.get(dispute_id)
        return dispute['timeline'] if dispute else []
    
    def get_active_disputes(self) -> List[Dict[str, Any]]:
        """Get all active disputes. / جميع النزاعات النشطة."""
        return [d for d in self._disputes.values() 
                if d['status'] not in ['closed']]
    
    def get_user_disputes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get disputes for a user. / نزاعات المستخدم."""
        return [d for d in self._disputes.values() 
                if d['opened_by'] == user_id or d['against'] == user_id]
    
    def get_mediator_stats(self, mediator_id: int) -> Dict[str, Any]:
        """Get mediator statistics. / إحصائيات الوسيط."""
        resolved = [d for d in self._disputes.values() 
                    if d.get('mediator_id') == mediator_id 
                    and d['status'] in ['resolved_buyer', 'resolved_seller', 'resolved_split']]
        return {
            'mediator_id': mediator_id,
            'total_resolved': len(resolved),
            'active_disputes': sum(1 for m in self._mediators if m['id'] == mediator_id for _ in [m.get('active_disputes', 0)])
        }
    
    def escalate_to_owner(self, dispute_id: int, reason: str) -> Dict[str, Any]:
        """Escalate dispute to owner. / تصعيد النزاع للمالك."""
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        dispute['escalated'] = True
        dispute['escalation_reason'] = reason
        dispute['escalated_at'] = datetime.now(timezone.utc).isoformat()
        dispute['timeline'].append({
            'event': 'escalated_to_owner',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': reason[:100]
        })
        
        logger.warning("dispute.escalated", dispute_id=dispute_id)
        return {'success': True, 'message': 'تم التصعيد للمالك'}
    
    def close_dispute(self, dispute_id: int, closed_by: int) -> Dict[str, Any]:
        """Close dispute permanently. / إغلاق النزاع نهائياً."""
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return {'success': False, 'error': 'not_found'}
        
        dispute['status'] = 'closed'
        dispute['closed_by'] = closed_by
        dispute['closed_at'] = datetime.now(timezone.utc)
        dispute['timeline'].append({
            'event': 'closed',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Closed by {closed_by}'
        })
        
        logger.info("dispute.closed", dispute_id=dispute_id)
        return {'success': True, 'message': 'تم إغلاق النزاع'}


dispute_resolution = DisputeResolution()

__all__ = ['DisputeResolution', 'dispute_resolution', 'DISPUTE_STATUSES']
