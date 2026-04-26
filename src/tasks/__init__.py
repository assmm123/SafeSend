"""
مهام Celery الخلفية
Celery Background Tasks

جميع المهام غير المتزامنة للنظام
"""

from src.tasks.watermark import (
    process_image_task,
    process_video_task,
    process_pdf_task,
)

from src.tasks.file import (
    assemble_chunks_task,
    virus_scan_task,
    cleanup_temp_files_task,
)

from src.tasks.payment import (
    scan_incoming_payments_task,
    process_payout_task,
    reconcile_transactions_task,
)

from src.tasks.notification import (
    send_email_batch_task,
    send_push_batch_task,
    send_daily_digests_task,
)

from src.tasks.backup import (
    backup_database_task,
    backup_files_task,
    backup_full_task,
)

from src.tasks.maintenance import (
    cleanup_expired_sessions_task,
    update_user_ratings_task,
    check_stalled_deals_task,
)

__all__ = [
    # Watermark
    "process_image_task",
    "process_video_task",
    "process_pdf_task",
    # File
    "assemble_chunks_task",
    "virus_scan_task",
    "cleanup_temp_files_task",
    # Payment
    "scan_incoming_payments_task",
    "process_payout_task",
    "reconcile_transactions_task",
    # Notification
    "send_email_batch_task",
    "send_push_batch_task",
    "send_daily_digests_task",
    # Backup
    "backup_database_task",
    "backup_files_task",
    "backup_full_task",
    # Maintenance
    "cleanup_expired_sessions_task",
    "update_user_ratings_task",
    "check_stalled_deals_task",
]
