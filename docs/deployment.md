# دليل النشر - Deployment Guide

## 📋 المتطلبات - Requirements

- Python 3.11+
- PostgreSQL 15+ (للإنتاج)
- Redis 7+ (اختياري)
- 2GB RAM minimum

---

## 🚀 النشر المحلي - Local Deployment

### 1. استنساخ المشروع
```bash
git clone <repository>
cd Safe1
```

2. إنشاء بيئة افتراضية

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows
```

3. تثبيت الاعتماديات

```bash
pip install -r requirements.txt
```

4. إعداد المتغيرات

```bash
cp .env.example .env
# عدل الملف حسب بيئتك
```

5. تهيئة قاعدة البيانات

```bash
alembic upgrade head
```

6. تشغيل التطبيق

```bash
python -m flask run
# أو
uvicorn src.api.app:app --reload
```

---

🐳 النشر باستخدام Docker

Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "5000"]
```

docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: nexus
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  app:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://nexus:${DB_PASSWORD}@postgres/nexus
      REDIS_URL: redis://redis:6379/0

volumes:
  postgres_data:
```

التشغيل

```bash
docker-compose up -d
```

---

☁️ النشر على VPS

1. تثبيت المتطلبات

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx postgresql redis-server
```

2. إعداد PostgreSQL

```bash
sudo -u postgres psql
CREATE USER nexus WITH PASSWORD 'secure_password';
CREATE DATABASE nexus OWNER nexus;
```

3. إعداد Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. إعداد systemd service

```
[Unit]
Description=Nexus API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/nexus
ExecStart=/var/www/nexus/venv/bin/uvicorn src.api.app:app --host 127.0.0.1 --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
```

5. تفعيل الخدمة

```bash
sudo systemctl enable nexus
sudo systemctl start nexus
```

---

📊 المراقبة - Monitoring

Health Check

```
GET /health
GET /health/detailed
```

Prometheus Metrics

```
GET /metrics
```

---

🔒 الأمان - Security

1. استخدم HTTPS دائماً (Let's Encrypt)
2. غير جميع المفاتيح الافتراضية
3. حدد CORS origins
4. فعل rate limiting
5. استخدم firewall

---

📦 النسخ الاحتياطي - Backup

```bash
# نسخ احتياطي يدوي
python -c "from src.app.models.backup import backup_full; backup_full()"

# نسخ احتياطي مجدول (cron)
0 2 * * * cd /var/www/nexus && python -c "from src.app.models.backup import backup_full; backup_full()"
```

