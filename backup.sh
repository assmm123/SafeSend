#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/Safe1/backups

# نسخ قاعدة البيانات
pg_dump safesend > $BACKUP_DIR/db_$DATE.sql 2>/dev/null

# نسخ الملفات
tar -czf $BACKUP_DIR/files_$DATE.tar.gz uploads/ 2>/dev/null

# نسخ .env
cp .env $BACKUP_DIR/env_$DATE.bak 2>/dev/null

# حذف النسخ الأقدم من 30 يوم
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: $DATE"
