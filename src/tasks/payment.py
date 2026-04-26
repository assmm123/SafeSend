"""
مهام المدفوعات
Payment Tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from src.app.models.deal_repository import DealRepository
from src.services.escrow import EscrowEngine
from src.services.tron import TronService

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='payment.scan_incoming',
    max_retries=2,
    default_retry_delay=60,
    queue='payment'
)
def scan_incoming_payments_task(self):
    """
    فحص المدفوعات الواردة
    Scan incoming payments
    """
    logger.info("Scanning incoming payments")
    
    try:
        tron = TronService()
        repo = DealRepository()
        
        pending_deals = repo.get_pending_funding()
        processed = 0
        
        for deal in pending_deals:
            result = tron.check_incoming_transaction(
                deal.escrow_address,
                deal.amount,
                deal.payment_memo
            )
            if result and result.verified:
                engine = EscrowEngine(tron, repo)
                engine.mark_as_funded(deal, result.tx_hash)
                processed += 1
        
        logger.info(f"Processed {processed} payments")
        return {'status': 'success', 'processed': processed}
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='payment.process_payout',
    max_retries=5,
    default_retry_delay=120,
    retry_backoff=True,
    retry_backoff_max=600,
    queue='payment'
)
def process_payout_task(self, deal_id: str, idempotency_key: str):
    """
    معالجة دفعة صادرة
    Process payout
    """
    logger.info(f"Processing payout for deal {deal_id}")
    
    try:
        tron = TronService()
        repo = DealRepository()
        engine = EscrowEngine(tron, repo)
        
        deal = repo.get_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        result = engine.process_payout(deal, idempotency_key)
        
        if result.success:
            logger.info(f"Payout successful: {result.tx_hash}")
            return {'status': 'success', 'tx_hash': result.tx_hash}
        else:
            raise Exception(result.error)
            
    except Exception as e:
        logger.error(f"Payout failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='payment.reconcile',
    queue='payment'
)
def reconcile_transactions_task(self):
    """
    مطابقة المعاملات
    Reconcile transactions
    """
    logger.info("Reconciling transactions")
    
    try:
        tron = TronService()
        repo = DealRepository()
        engine = EscrowEngine(tron, repo)
        
        report = engine.reconcile_transactions()
        
        logger.info(f"Reconciliation complete: {report.matched}/{report.total} matched")
        return {'status': 'success', 'report': report.to_dict()}
        
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        return {'status': 'error', 'error': str(e)}
