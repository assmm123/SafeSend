"""
مهام الإشعارات
Notification Tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from src.services.notification import NotificationService

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='notification.send_email_batch',
    max_retries=3,
    default_retry_delay=60,
    queue='notification'
)
def send_email_batch_task(self, recipients: list, subject: str, body: str):
    """
    إرسال بريد إلكتروني دفعة
    Send batch emails
    """
    logger.info(f"Sending batch email to {len(recipients)} recipients")
    
    try:
        service = NotificationService()
        success = 0
        
        for recipient in recipients:
            result = service.send_email(recipient, subject, body)
            if result.success:
                success += 1
        
        logger.info(f"Sent {success}/{len(recipients)} emails")
        return {'status': 'success', 'sent': success, 'total': len(recipients)}
        
    except Exception as e:
        logger.error(f"Batch email failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='notification.send_push_batch',
    max_retries=3,
    default_retry_delay=30,
    queue='notification'
)
def send_push_batch_task(self, user_ids: list, title: str, body: str, data: dict = None):
    """
    إرسال Push إشعارات دفعة
    Send batch push notifications
    """
    logger.info(f"Sending push to {len(user_ids)} users")
    
    try:
        service = NotificationService()
        result = service.send_to_multiple(user_ids, title, body, data)
        
        logger.info(f"Push results: {result.success}/{result.total} sent")
        return {'status': 'success', 'result': result.to_dict()}
        
    except Exception as e:
        logger.error(f"Batch push failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='notification.send_daily_digests',
    queue='notification'
)
def send_daily_digests_task(self):
    """
    إرسال الملخصات اليومية
    Send daily digests
    """
    logger.info("Sending daily digests")
    
    try:
        service = NotificationService()
        sent = 0
        
        users = service.get_users_with_digest_enabled()
        
        for user in users:
            result = service.send_digest(user.id, user.email, 'daily')
            if result.success:
                sent += 1
        
        logger.info(f"Sent {sent} daily digests")
        return {'status': 'success', 'sent': sent}
        
    except Exception as e:
        logger.error(f"Daily digests failed: {e}")
        return {'status': 'error', 'error': str(e)}
