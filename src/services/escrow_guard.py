"""
Escrow Guard Service - SafeSend
حارس الوساطة المالية - SafeSend

Manages fund holds, releases (normal + instant with owner approval), and auto-release.
يدير تجميد الأموال وتحريرها (عادي + فوري بموافقة المالك) والتحرير التلقائي.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)

HOLD_EXPIRY_DAYS = 14
SMALL_AMOUNT_THRESHOLD = 100.00

class EscrowGuard:
    """
    Escrow fund guardian with instant release capability.
    حارس أموال الوساطة مع إمكانية التحرير الفوري.
    
    Owner can approve instant release for emergencies.
    يمكن للمالك الموافقة على التحرير الفوري للحالات الطارئة.
    """
    
    def __init__(self):
        self._holds: Dict[str, Dict[str, Any]] = {}
        self._instant_requests: Dict[str, Dict[str, Any]] = {}
        self._hold_counter = 0
    
    # ============================================================
    # Hold Funds
    # ============================================================
    
    def hold_funds(self, deal_id: int, amount: float, buyer_id: int, seller_id: int) -> Dict[str, Any]:
        """
        Place funds in escrow hold.
        وضع الأموال في حساب الوساطة.
        """
        self._hold_counter += 1
        hold_id = f"HOLD-{self._hold_counter:06d}"
        
        hold = {
            'hold_id': hold_id,
            'deal_id': deal_id,
            'amount': amount,
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'status': 'held',
            'created_at': datetime.now(timezone.utc),
            'release_after': datetime.now(timezone.utc) + timedelta(hours=24),
            'auto_release_after': datetime.now(timezone.utc) + timedelta(days=HOLD_EXPIRY_DAYS),
            'released_at': None,
            'released_by': None,
            'release_type': None,
            'history': [{
                'action': 'hold_created',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': f'Funds held: ${amount}'
            }]
        }
        
        self._holds[hold_id] = hold
        logger.info("escrow.hold_created", hold_id=hold_id, deal_id=deal_id, amount=amount)
        
        return hold
    
    # ============================================================
    # Release Funds (Normal - 24h wait)
    # ============================================================
    
    def release_funds(self, hold_id: str, approved_by: int) -> Dict[str, Any]:
        """
        Release funds after normal 24h period.
        تحرير الأموال بعد فترة 24 ساعة العادية.
        """
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'hold_not_found', 'message': 'تجميد غير موجود'}
        
        if hold['status'] != 'held':
            return {'success': False, 'error': 'invalid_status', 'message': f'الحالة الحالية: {hold["status"]}'}
        
        now = datetime.now(timezone.utc)
        if now < hold['release_after']:
            remaining = hold['release_after'] - now
            hours = int(remaining.total_seconds() / 3600)
            return {
                'success': False, 'error': 'too_early',
                'message': f'يجب الانتظار {hours} ساعة أخرى',
                'remaining_hours': hours
            }
        
        hold['status'] = 'released'
        hold['released_at'] = now
        hold['released_by'] = approved_by
        hold['release_type'] = 'normal'
        hold['history'].append({
            'action': 'released',
            'timestamp': now.isoformat(),
            'details': f'Released by: {approved_by}'
        })
        
        logger.info("escrow.released", hold_id=hold_id, approved_by=approved_by)
        
        return {'success': True, 'message': 'تم تحرير الأموال', 'hold_id': hold_id}
    
    # ============================================================
    # Instant Release (Owner Approval Required)
    # ============================================================
    
    def request_instant_release(self, hold_id: str, requested_by: int, reason: str = 'urgent') -> Dict[str, Any]:
        """
        Request instant release - notifies owner for approval.
        طلب تحرير فوري - إشعار للمالك للموافقة.
        """
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'hold_not_found', 'message': 'تجميد غير موجود'}
        
        if hold['status'] != 'held':
            return {'success': False, 'error': 'invalid_status', 'message': f'الحالة: {hold["status"]}'}
        
        # Small amounts auto-approve
        if hold['amount'] <= SMALL_AMOUNT_THRESHOLD:
            return self.owner_approve_release(hold_id, 0, 'auto_approved_small_amount')
        
        self._instant_requests[hold_id] = {
            'hold_id': hold_id,
            'requested_by': requested_by,
            'reason': reason,
            'amount': hold['amount'],
            'deal_id': hold['deal_id'],
            'seller_id': hold['seller_id'],
            'buyer_id': hold['buyer_id'],
            'requested_at': datetime.now(timezone.utc),
            'status': 'pending_owner_approval'
        }
        
        logger.warning("escrow.instant_release_requested", 
                       hold_id=hold_id, requested_by=requested_by, reason=reason)
        
        return {
            'success': True,
            'message': 'تم إرسال طلب تحرير فوري للمالك',
            'message_ar': 'Instant release requested - waiting for owner approval',
            'requires_owner_approval': True,
            'hold_id': hold_id
        }
    
    def owner_approve_release(self, hold_id: str, owner_id: int, notes: str = '') -> Dict[str, Any]:
        """
        Owner approves instant release - funds released immediately.
        موافقة المالك على التحرير الفوري - تحرير الأموال فوراً.
        """
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'hold_not_found', 'message': 'تجميد غير موجود'}
        
        if hold['status'] != 'held':
            return {'success': False, 'error': 'invalid_status', 'message': f'الحالة: {hold["status"]}'}
        
        now = datetime.now(timezone.utc)
        hold['status'] = 'released'
        hold['released_at'] = now
        hold['released_by'] = owner_id
        hold['release_type'] = 'instant_owner_approved'
        hold['history'].append({
            'action': 'instant_released',
            'timestamp': now.isoformat(),
            'details': f'Owner approved: {owner_id} - {notes}'
        })
        
        # Clear instant request
        self._instant_requests.pop(hold_id, None)
        
        logger.info("escrow.instant_released", hold_id=hold_id, owner_id=owner_id)
        
        return {
            'success': True,
            'message': 'تم تحرير الأموال فوراً بموافقة المالك',
            'hold_id': hold_id,
            'released_at': now.isoformat()
        }
    
    def owner_reject_release(self, hold_id: str, owner_id: int, reason: str = '') -> Dict[str, Any]:
        """
        Owner rejects instant release request.
        رفض المالك لطلب التحرير الفوري.
        """
        request = self._instant_requests.pop(hold_id, None)
        if not request:
            return {'success': False, 'error': 'request_not_found', 'message': 'طلب غير موجود'}
        
        hold = self._holds.get(hold_id)
        if hold:
            hold['history'].append({
                'action': 'instant_rejected',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': f'Owner rejected: {owner_id} - {reason}'
            })
        
        logger.info("escrow.instant_rejected", hold_id=hold_id, owner_id=owner_id, reason=reason)
        
        return {
            'success': True,
            'message': 'تم رفض طلب التحرير الفوري',
            'hold_id': hold_id
        }
    
    # ============================================================
    # Auto Release
    # ============================================================
    
    def auto_release_after_days(self, hold_id: str, days: int = HOLD_EXPIRY_DAYS) -> Dict[str, Any]:
        """
        Auto-release funds after expiry period.
        تحرير تلقائي للأموال بعد انتهاء المدة.
        """
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'hold_not_found', 'message': 'تجميد غير موجود'}
        
        if hold['status'] != 'held':
            return {'success': False, 'error': 'invalid_status', 'message': f'الحالة: {hold["status"]}'}
        
        now = datetime.now(timezone.utc)
        if now < hold['auto_release_after']:
            return {'success': False, 'error': 'not_expired', 'message': 'لم تنته المدة بعد'}
        
        hold['status'] = 'released'
        hold['released_at'] = now
        hold['released_by'] = 0  # System
        hold['release_type'] = 'auto_expired'
        hold['history'].append({
            'action': 'auto_released',
            'timestamp': now.isoformat(),
            'details': f'Auto-released after {days} days'
        })
        
        logger.info("escrow.auto_released", hold_id=hold_id)
        
        return {'success': True, 'message': 'تم التحرير التلقائي', 'hold_id': hold_id}
    
    # ============================================================
    # Dispute Handling
    # ============================================================
    
    def freeze_for_dispute(self, hold_id: str, dispute_id: int) -> Dict[str, Any]:
        """
        Freeze funds when dispute is opened.
        تجميد الأموال عند فتح نزاع.
        """
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'hold_not_found'}
        
        hold['status'] = 'disputed'
        hold['dispute_id'] = dispute_id
        hold['frozen_at'] = datetime.now(timezone.utc)
        hold['history'].append({
            'action': 'frozen_for_dispute',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': f'Dispute #{dispute_id}'
        })
        
        logger.warning("escrow.dispute_frozen", hold_id=hold_id, dispute_id=dispute_id)
        
        return {'success': True, 'message': 'تم تجميد الأموال للنزاع', 'hold_id': hold_id}
    
    # ============================================================
    # Status & Queries
    # ============================================================
    
    def get_hold_status(self, hold_id: str) -> Dict[str, Any]:
        """Get current hold status. / حالة التجميد الحالية."""
        hold = self._holds.get(hold_id)
        if not hold:
            return {'success': False, 'error': 'not_found'}
        
        now = datetime.now(timezone.utc)
        return {
            'hold_id': hold_id,
            'status': hold['status'],
            'amount': hold['amount'],
            'deal_id': hold['deal_id'],
            'created_at': hold['created_at'].isoformat(),
            'can_release_normal': hold['status'] == 'held' and now >= hold['release_after'],
            'can_request_instant': hold['status'] == 'held' and now < hold['release_after'],
            'remaining_hours': max(0, int((hold['release_after'] - now).total_seconds() / 3600)) if now < hold['release_after'] else 0,
            'auto_release_date': hold['auto_release_after'].isoformat(),
            'has_pending_instant_request': hold_id in self._instant_requests
        }
    
    def get_pending_instant_requests(self) -> List[Dict[str, Any]]:
        """Get all pending instant release requests for owner review."""
        return [
            {
                'hold_id': hid,
                'requested_by': req['requested_by'],
                'reason': req['reason'],
                'amount': req['amount'],
                'deal_id': req['deal_id'],
                'requested_at': req['requested_at'].isoformat()
            }
            for hid, req in self._instant_requests.items()
        ]
    
    def get_hold_history(self, hold_id: str) -> List[Dict[str, Any]]:
        """Get hold event history. / سجل أحداث التجميد."""
        hold = self._holds.get(hold_id)
        return hold['history'] if hold else []


escrow_guard = EscrowGuard()

__all__ = ['EscrowGuard', 'escrow_guard', 'HOLD_EXPIRY_DAYS', 'SMALL_AMOUNT_THRESHOLD']
