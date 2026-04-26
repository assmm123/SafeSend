"""
تطبيق Celery للمهام الخلفية
Celery Application for Background Tasks

يدير المهام غير المتزامنة والجدولة الدورية مع:
- توجيه المهام (Task Routing)
- جدولة المهام الدورية (Celery Beat)
- دعم Termux مع إعدادات مخفضة
- تكامل مع Flask
- مراقبة المهام عبر Signals
"""

import os
from typing import Dict, List, Optional, Union

from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    worker_ready,
    worker_shutdown,
)
from kombu import Queue, Exchange

from src.app.models.config import get_config
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# دوال مساعدة للإعدادات
# ============================================

def get_redis_url() -> str:
    """
    الحصول على عنوان Redis من متغيرات البيئة
    Get Redis URL from environment variables
    
    Returns:
        str: عنوان Redis
    """
    return os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


def is_termux() -> bool:
    """
    التحقق مما إذا كنا نعمل على Termux
    Check if running on Termux
    
    Returns:
        bool: True إذا كنا على Termux
    """
    return bool(os.environ.get('TERMUX_VERSION'))


# ============================================
# إنشاء تطبيق Celery
# ============================================

def create_celery(app_name: str = 'safesend') -> Celery:
    """
    إنشاء تطبيق Celery مهيأ بالكامل
    Create fully configured Celery application
    
    Args:
        app_name (str): اسم التطبيق
        
    Returns:
        Celery: تطبيق Celery مهيأ
    """
    redis_url = get_redis_url()
    
    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=['src.tasks']
    )
    
    # ============================================
    # إعدادات Celery الأساسية
    # ============================================
    
    celery.conf.update(
        # التسلسل
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        
        # الوقت
        timezone='UTC',
        enable_utc=True,
        
        # تتبع المهام
        task_track_started=True,
        task_send_sent_event=True,
        
        # حدود الوقت
        task_time_limit=1800,
        task_soft_time_limit=1500,
        
        # إدارة workers
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_send_task_events=True,
        
        # تأكيد المهام
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        
        # نتائج المهام
        result_expires=86400,
        result_extended=True,
        
        # إعادة المحاولة
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
    )
    
    # ============================================
    # إعدادات Termux (موارد محدودة)
    # ============================================
    
    if is_termux():
        celery.conf.update(
            worker_concurrency=2,
            worker_max_memory_per_child=256000,
            broker_pool_limit=10,
        )
        logger.info("Celery configured for Termux (limited resources)")
    else:
        celery.conf.update(
            worker_concurrency=4,
            broker_pool_limit=50,
        )
    
    # ============================================
    # توجيه المهام (Task Routing)
    # ============================================
    
    default_exchange = Exchange('default', type='direct')
    watermark_exchange = Exchange('watermark', type='direct')
    file_exchange = Exchange('file', type='direct')
    payment_exchange = Exchange('payment', type='direct')
    notification_exchange = Exchange('notification', type='direct')
    backup_exchange = Exchange('backup', type='direct')
    
    celery.conf.task_queues = (
        Queue('default', default_exchange, routing_key='default'),
        Queue('watermark', watermark_exchange, routing_key='watermark'),
        Queue('file', file_exchange, routing_key='file'),
        Queue('payment', payment_exchange, routing_key='payment'),
        Queue('notification', notification_exchange, routing_key='notification'),
        Queue('backup', backup_exchange, routing_key='backup'),
    )
    
    celery.conf.task_routes = {
        'watermark.*': {'queue': 'watermark'},
        'file.*': {'queue': 'file'},
        'payment.*': {'queue': 'payment'},
        'notification.*': {'queue': 'notification'},
        'backup.*': {'queue': 'backup'},
    }
    
    # ============================================
    # جدولة المهام الدورية (Celery Beat)
    # ============================================
    
    celery.conf.beat_schedule = {
        # فحص الصفقات المنتهية - كل ساعة
        'check-expired-deals': {
            'task': 'escrow.check_expired_deals',
            'schedule': crontab(minute='0', hour='*/1'),
            'options': {'queue': 'payment'}
        },
        # معالجة الصفقات المتوقفة - كل 6 ساعات
        'process-stalled-deals': {
            'task': 'escrow.process_stalled_deals',
            'schedule': crontab(minute='0', hour='*/6'),
            'options': {'queue': 'payment'}
        },
        # مطابقة المعاملات - يومياً 2 صباحاً
        'reconcile-transactions': {
            'task': 'escrow.reconcile_transactions',
            'schedule': crontab(minute='0', hour='2'),
            'options': {'queue': 'payment'}
        },
        # تنظيف الملفات المؤقتة - يومياً 3 صباحاً
        'cleanup-temp-files': {
            'task': 'file.cleanup_temp_files',
            'schedule': crontab(minute='0', hour='3'),
            'options': {'queue': 'file'}
        },
        # تحديث تعريفات الفيروسات - يومياً 4 صباحاً
        'update-virus-definitions': {
            'task': 'virus.update_definitions',
            'schedule': crontab(minute='0', hour='4'),
            'options': {'queue': 'file'}
        },
        # نسخ احتياطي لقاعدة البيانات - يومياً 1 صباحاً
        'backup-database': {
            'task': 'backup.database',
            'schedule': crontab(minute='0', hour='1'),
            'options': {'queue': 'backup'}
        },
        # نسخ احتياطي كامل - أسبوعياً الأحد 2 صباحاً
        'backup-full': {
            'task': 'backup.full',
            'schedule': crontab(minute='0', hour='2', day_of_week='0'),
            'options': {'queue': 'backup'}
        },
        # تنظيف الجلسات المنتهية - كل 6 ساعات
        'cleanup-sessions': {
            'task': 'maintenance.cleanup_sessions',
            'schedule': crontab(minute='30', hour='*/6'),
            'options': {'queue': 'default'}
        },
        # إرسال الملخصات اليومية - يومياً 9 صباحاً
        'send-daily-digests': {
            'task': 'notification.send_daily_digests',
            'schedule': crontab(minute='0', hour='9'),
            'options': {'queue': 'notification'}
        },
    }
    
    return celery


# ============================================
# إنشاء التطبيق العام
# ============================================

celery_app = create_celery()


# ============================================
# Signals للمراقبة
# ============================================

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """قبل بدء المهمة / Before task starts"""
    logger.debug(f"Task starting: {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    """بعد انتهاء المهمة / After task completes"""
    logger.debug(f"Task completed: {task.name}[{task_id}] state={state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """عند فشل المهمة / When task fails"""
    logger.error(f"Task failed: {sender.name}[{task_id}] error={exception}")


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """عند جهوزية worker / When worker is ready"""
    logger.info(f"Worker ready: {sender.hostname}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """عند إيقاف worker / When worker shuts down"""
    logger.info(f"Worker shutdown: {sender.hostname}")


# ============================================
# تكامل مع Flask
# ============================================

def init_celery(app):
    """
    تهيئة Celery مع تطبيق Flask
    Initialize Celery with Flask application
    
    Args:
        app: تطبيق Flask
        
    Returns:
        Celery: تطبيق Celery مع سياق Flask
    """
    celery = create_celery(app.import_name)
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """مهمة مع سياق Flask / Task with Flask context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


# ============================================
# دوال مساعدة لإدارة المهام
# ============================================

def get_task_status(task_id: str) -> Dict[str, Union[str, bool, None]]:
    """
    الحصول على حالة مهمة
    Get task status
    
    Args:
        task_id (str): معرف المهمة
        
    Returns:
        Dict: حالة المهمة
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        'id': task_id,
        'status': result.status,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'result': str(result.result) if result.ready() else None,
        'traceback': result.traceback,
    }


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """
    إلغاء مهمة
    Revoke a task
    
    Args:
        task_id (str): معرف المهمة
        terminate (bool): إنهاء المهمة بالقوة
        
    Returns:
        bool: نجاح الإلغاء
    """
    celery_app.control.revoke(task_id, terminate=terminate)
    return True


def get_active_tasks() -> Dict[str, Dict]:
    """
    جلب المهام النشطة
    Get active tasks
    
    Returns:
        Dict: المهام النشطة والمجدولة والمحجوزة
    """
    inspect = celery_app.control.inspect()
    
    if not inspect:
        return {'active': {}, 'scheduled': {}, 'reserved': {}}
    
    active = inspect.active() or {}
    scheduled = inspect.scheduled() or {}
    reserved = inspect.reserved() or {}
    
    return {
        'active': active,
        'scheduled': scheduled,
        'reserved': reserved,
    }


def get_worker_stats() -> Dict[str, Dict]:
    """
    جلب إحصائيات workers
    Get worker statistics
    
    Returns:
        Dict: إحصائيات workers والمهام المسجلة
    """
    inspect = celery_app.control.inspect()
    
    if not inspect:
        return {'stats': {}, 'registered_tasks': {}}
    
    stats = inspect.stats() or {}
    registered = inspect.registered() or {}
    
    return {
        'stats': stats,
        'registered_tasks': registered,
    }


def purge_queue(queue_name: Optional[str] = None) -> int:
    """
    تفريغ قائمة الانتظار
    Purge queue
    
    Args:
        queue_name (Optional[str]): اسم القائمة (None للكل)
        
    Returns:
        int: عدد المهام المحذوفة
    """
    if queue_name:
        return celery_app.control.purge(queue=queue_name)
    return celery_app.control.purge()


def ping_workers() -> Dict[str, Dict]:
    """
    فحص اتصال workers
    Ping all workers
    
    Returns:
        Dict: استجابة workers
    """
    inspect = celery_app.control.inspect()
    
    if not inspect:
        return {}
    
    return inspect.ping() or {}


__all__ = [
    'celery_app',
    'create_celery',
    'init_celery',
    'get_task_status',
    'revoke_task',
    'get_active_tasks',
    'get_worker_stats',
    'purge_queue',
    'ping_workers',
]
