"""
خدمة الإشعارات المتقدمة
Advanced Notification Service

مركز إدارة جميع إشعارات النظام:
- بريد إلكتروني (SMTP / SendGrid / AWS SES)
- Push Notifications (FCM / Web Push)
- SMS (Twilio / AWS SNS)
- قوالب Jinja2
- جدولة وتجميع
- تتبع وإعادة محاولة
"""

import hashlib
import json
import os
import re
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

class NotificationType(Enum):
    """أنواع الإشعارات"""
    DEAL_CREATED = "deal_created"
    PAYMENT_RECEIVED = "payment_received"
    FUNDS_VERIFIED = "funds_verified"
    WORK_DELIVERED = "work_delivered"
    WORK_APPROVED = "work_approved"
    PAYOUT_PROCESSING = "payout_processing"
    PAYOUT_SENT = "payout_sent"
    PAYOUT_CONFIRMED = "payout_confirmed"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"
    NEW_MESSAGE = "new_message"
    VERIFY_EMAIL = "verify_email"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    DEAL_EXPIRED = "deal_expired"
    DEAL_STALLED = "deal_stalled"
    ADMIN_ALERT = "admin_alert"
    DIGEST_DAILY = "digest_daily"
    DIGEST_WEEKLY = "digest_weekly"


class NotificationPriority(Enum):
    """أولويات الإشعارات"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class NotificationChannel(Enum):
    """قنوات الإرسال"""
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class EmailProviderType(Enum):
    """أنواع مزودي البريد"""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    SES = "ses"
    MAILGUN = "mailgun"


# إعدادات افتراضية
DEFAULT_SMTP_PORT = 587
DEFAULT_MAX_RETRIES = 3
DEFAULT_COOLDOWN_SECONDS = 60
DEFAULT_DAILY_LIMIT = 50
DEFAULT_BATCH_SIZE = 100


# ============================================
# Data Classes
# ============================================

@dataclass
class Notification:
    """إشعار"""
    id: str
    user_id: str
    type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    subject: Optional[str] = None
    content: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    scheduled_for: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value,
            "channel": self.channel.value,
            "priority": self.priority.value,
            "subject": self.subject,
            "content": self.content,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> 'Notification':
        d = json.loads(data)
        return cls(
            id=d["id"],
            user_id=d["user_id"],
            type=NotificationType(d["type"]),
            channel=NotificationChannel(d["channel"]),
            priority=NotificationPriority(d.get("priority", 5)),
            subject=d.get("subject"),
            content=d.get("content"),
            data=d.get("data", {}),
            created_at=datetime.fromisoformat(d["created_at"]),
            scheduled_for=datetime.fromisoformat(d["scheduled_for"]) if d.get("scheduled_for") else None,
        )


@dataclass
class NotificationResult:
    """نتيجة إرسال إشعار"""
    success: bool
    notification_id: str
    channel: NotificationChannel
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: datetime = field(default_factory=utc_now)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "notification_id": self.notification_id,
            "channel": self.channel.value,
            "provider": self.provider,
            "message_id": self.message_id,
            "error": self.error,
            "sent_at": self.sent_at.isoformat(),
        }


@dataclass
class UserPreferences:
    """تفضيلات المستخدم للإشعارات"""
    user_id: str
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    push_tokens: List[str] = field(default_factory=list)
    sms_types: List[str] = field(default_factory=list)
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    timezone: str = "UTC"


@dataclass
class HealthStatus:
    """حالة صحة الخدمة"""
    status: str
    email_provider: str
    email_available: bool
    push_available: bool
    sms_available: bool
    queue_size: int
    retry_queue_size: int
    circuit_breaker_state: str


# ============================================
# Exceptions
# ============================================

class NotificationError(Exception):
    pass


class EmailProviderError(NotificationError):
    pass


class PushProviderError(NotificationError):
    pass


class SMSProviderError(NotificationError):
    pass


# ============================================
# Email Providers
# ============================================

class BaseEmailProvider:
    """مزود بريد أساسي"""
    
    def __init__(self, name: str):
        self.name = name
    
    def send(self, to: str, subject: str, html: str, text: Optional[str] = None) -> tuple:
        raise NotImplementedError


class SMTPEmailProvider(BaseEmailProvider):
    """مزود SMTP"""
    
    def __init__(
        self,
        host: str,
        port: int = DEFAULT_SMTP_PORT,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        from_email: str = "noreply@safesend.com"
    ):
        super().__init__("smtp")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
    
    def send(self, to: str, subject: str, html: str, text: Optional[str] = None) -> tuple:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to
            
            if text:
                msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            return True, None
        except Exception as e:
            return False, str(e)


class SendGridProvider(BaseEmailProvider):
    """مزود SendGrid"""
    
    def __init__(self, api_key: str, from_email: str = "noreply@safesend.com"):
        super().__init__("sendgrid")
        self.api_key = api_key
        self.from_email = from_email
    
    def send(self, to: str, subject: str, html: str, text: Optional[str] = None) -> tuple:
        try:
            import requests
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": self.from_email},
                "subject": subject,
                "content": [{"type": "text/html", "value": html}]
            }
            if text:
                data["content"].append({"type": "text/plain", "value": text})
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.status_code == 202, None if response.status_code == 202 else response.text
        except Exception as e:
            return False, str(e)


# ============================================
# Notification Service
# ============================================

class NotificationService:
    """خدمة الإشعارات المتقدمة"""
    
    def __init__(
        self,
        email_provider: Optional[BaseEmailProvider] = None,
        push_service: Any = None,
        sms_provider: Any = None,
        redis_client: Any = None,
        template_dir: str = "./templates",
        circuit_breaker: Optional[CircuitBreaker] = None,
        from_email: str = "noreply@safesend.com",
        admin_email: str = "admin@safesend.com",
        base_url: str = "https://safesend.com"
    ):
        self.email_provider = email_provider
        self.push_service = push_service
        self.sms_provider = sms_provider
        self.redis = redis_client
        self.from_email = from_email
        self.admin_email = admin_email
        self.base_url = base_url
        
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="notification_service", failure_threshold=3, timeout=30.0
        )
        
        # إعداد Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # إعدادات القنوات
        self._cooldowns = {
            NotificationType.NEW_MESSAGE: 30,
            NotificationType.DEAL_CREATED: 0,
            NotificationType.ADMIN_ALERT: 0,
        }
        
        self._daily_limits = {
            NotificationType.NEW_MESSAGE: 100,
            NotificationType.DEAL_CREATED: 20,
            NotificationType.ADMIN_ALERT: 500,
        }
        
        logger.info(f"NotificationService initialized: email={bool(email_provider)} push={bool(push_service)}")
    
    # ============================================
    # دوال القوالب
    # ============================================
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> tuple:
        """تقديم قالب Jinja2"""
        try:
            template = self.jinja_env.get_template(f"{template_name}.html")
            html = template.render({
                **context,
                "app_name": "SafeSend",
                "base_url": self.base_url,
                "support_email": self.from_email,
                "year": datetime.now().year,
            })
            return html, None
        except Exception as e:
            return "", str(e)
    
    def render_subject(self, notification_type: NotificationType, context: Dict[str, Any]) -> str:
        """توليد عنوان البريد"""
        subjects = {
            NotificationType.WELCOME: "Welcome to SafeSend! 🎉",
            NotificationType.VERIFY_EMAIL: "Verify your email address",
            NotificationType.PASSWORD_RESET: "Reset your password",
            NotificationType.DEAL_CREATED: f"New deal created: {context.get('deal_title', '')}",
            NotificationType.PAYMENT_RECEIVED: f"Payment received for {context.get('deal_title', '')}",
            NotificationType.WORK_DELIVERED: f"Work delivered for {context.get('deal_title', '')}",
            NotificationType.PAYOUT_SENT: f"Your payout has been sent! 💰",
            NotificationType.NEW_MESSAGE: f"New message from {context.get('sender_name', '')}",
            NotificationType.DISPUTE_OPENED: f"Dispute opened for {context.get('deal_title', '')}",
        }
        return subjects.get(notification_type, "SafeSend Notification")
    
    # ============================================
    # إرسال البريد
    # ============================================
    
    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        notification_id: Optional[str] = None,
        track: bool = False
    ) -> NotificationResult:
        """إرسال بريد إلكتروني"""
        nid = notification_id or generate_id("email")
        
        if not self.email_provider:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.EMAIL,
                provider="none", error="No email provider configured"
            )
        
        try:
            # إضافة tracking
            if track:
                pixel = f'<img src="{self.base_url}/api/v1/track/open/{nid}" width="1" height="1" />'
                html += pixel
            
            def _send():
                return self.email_provider.send(to, subject, html, text)
            
            success, error = self.circuit_breaker.call(_send)
            
            result = NotificationResult(
                success=success, notification_id=nid, channel=NotificationChannel.EMAIL,
                provider=self.email_provider.name, error=error
            )
            
            self._record_metrics("email", success)
            
            if success:
                logger.info(f"Email sent: {to} - {subject}")
            else:
                logger.error(f"Email failed: {to} - {error}")
            
            return result
            
        except CircuitBreakerOpenError:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.EMAIL,
                provider=self.email_provider.name, error="Circuit breaker open"
            )
    
    def send_templated_email(
        self,
        to: str,
        notification_type: NotificationType,
        context: Dict[str, Any],
        track: bool = True
    ) -> NotificationResult:
        """إرسال بريد باستخدام قالب"""
        nid = generate_id("email")
        
        html, error = self.render_template(notification_type.value, context)
        if error:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.EMAIL,
                provider=self.email_provider.name if self.email_provider else "none",
                error=f"Template error: {error}"
            )
        
        subject = self.render_subject(notification_type, context)
        
        return self.send_email(to, subject, html, notification_id=nid, track=track)
    
    # ============================================
    # إرسال Push
    # ============================================
    
    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """إرسال Push Notification"""
        nid = generate_id("push")
        
        if not self.push_service:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.PUSH,
                provider="none", error="No push service configured"
            )
        
        try:
            success, error = self.push_service.send(user_id, title, body, data, priority.value)
            
            result = NotificationResult(
                success=success, notification_id=nid, channel=NotificationChannel.PUSH,
                provider="fcm", error=error
            )
            
            self._record_metrics("push", success)
            return result
            
        except Exception as e:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.PUSH,
                provider="fcm", error=str(e)
            )
    
    # ============================================
    # إرسال SMS
    # ============================================
    
    def send_sms(self, phone: str, message: str) -> NotificationResult:
        """إرسال SMS"""
        nid = generate_id("sms")
        
        if not self.sms_provider:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.SMS,
                provider="none", error="No SMS provider configured"
            )
        
        try:
            success, error = self.sms_provider.send(phone, message)
            
            result = NotificationResult(
                success=success, notification_id=nid, channel=NotificationChannel.SMS,
                provider="twilio", error=error
            )
            
            self._record_metrics("sms", success)
            return result
            
        except Exception as e:
            return NotificationResult(
                success=False, notification_id=nid, channel=NotificationChannel.SMS,
                provider="twilio", error=str(e)
            )
    
    # ============================================
    # إشعارات موحدة
    # ============================================
    
    def notify_user(
        self,
        user: Any,
        notification_type: NotificationType,
        data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> List[NotificationResult]:
        """إشعار موحد للمستخدم عبر القنوات المفضلة"""
        results = []
        
        # تحديد القنوات
        if channels is None:
            channels = self._get_channels_for_type(notification_type)
        
        # التحقق من التفضيلات
        prefs = self._get_user_preferences(str(user.id)) if hasattr(user, 'id') else None
        
        for channel in channels:
            if channel == NotificationChannel.EMAIL and hasattr(user, 'email') and user.email:
                if not prefs or prefs.email_enabled:
                    result = self.send_templated_email(user.email, notification_type, data)
                    results.append(result)
            
            elif channel == NotificationChannel.PUSH and hasattr(user, 'id'):
                if not prefs or prefs.push_enabled:
                    title = data.get("title", self.render_subject(notification_type, data))
                    body = data.get("body", data.get("message", ""))
                    result = self.send_push(str(user.id), title, body, data, priority)
                    results.append(result)
            
            elif channel == NotificationChannel.SMS and hasattr(user, 'phone') and user.phone:
                if prefs and prefs.sms_enabled:
                    message = data.get("sms_message", data.get("message", ""))
                    if message:
                        result = self.send_sms(user.phone, message)
                        results.append(result)
        
        return results
    
    def notify_admin(
        self,
        level: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.HIGH
    ) -> List[NotificationResult]:
        """إشعار المشرفين"""
        results = []
        
        # بريد إلكتروني
        html, _ = self.render_template("admin_alert", {
            "level": level,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "timestamp": utc_now().isoformat()
        })
        
        result = self.send_email(
            self.admin_email,
            f"[{level.upper()}] {title}",
            html,
            notification_id=generate_id("admin")
        )
        results.append(result)
        
        # Push للمشرفين
        if self.push_service:
            result = self.send_push(
                "admin",
                f"[{level.upper()}] {title}",
                message[:100],
                data=metadata or {},
                priority=priority
            )
            results.append(result)
        
        return results
    
    # ============================================
    # جدولة وتجميع
    # ============================================
    
    def schedule_notification(
        self,
        notification: Notification,
        send_at: datetime
    ) -> bool:
        """جدولة إشعار للإرسال لاحقاً"""
        if not self.redis:
            return False
        
        notification.scheduled_for = send_at
        score = send_at.timestamp()
        self.redis.zadd("notifications:scheduled", {notification.to_json(): score})
        
        logger.info(f"Notification scheduled: {notification.id} at {send_at}")
        return True
    
    def queue_notification(self, notification: Notification) -> bool:
        """إضافة إشعار إلى قائمة الانتظار"""
        if not self.redis:
            return False
        
        self.redis.lpush("notifications:queue", notification.to_json())
        return True
    
    def queue_for_digest(self, user_id: str, notification: Notification):
        """إضافة إشعار إلى ملخص يومي"""
        if not self.redis:
            return
        
        key = f"digest:{user_id}:{utc_now().strftime('%Y%m%d')}"
        self.redis.rpush(key, notification.to_json())
        self.redis.expire(key, 86400 * 7)  # 7 أيام
    
    def send_digest(self, user_id: str, email: str, frequency: str = "daily") -> NotificationResult:
        """إرسال ملخص الإشعارات"""
        if not self.redis:
            return NotificationResult(
                success=False, notification_id="digest", channel=NotificationChannel.EMAIL,
                provider="none", error="Redis not configured"
            )
        
        date_str = utc_now().strftime('%Y%m%d')
        if frequency == "weekly":
            # جمع آخر 7 أيام
            notifications = []
            for i in range(7):
                day = (utc_now() - timedelta(days=i)).strftime('%Y%m%d')
                key = f"digest:{user_id}:{day}"
                data = self.redis.lrange(key, 0, -1)
                notifications.extend([Notification.from_json(n) for n in data])
        else:
            key = f"digest:{user_id}:{date_str}"
            data = self.redis.lrange(key, 0, -1)
            notifications = [Notification.from_json(n) for n in data]
        
        if not notifications:
            return NotificationResult(
                success=True, notification_id="digest", channel=NotificationChannel.EMAIL,
                provider=self.email_provider.name if self.email_provider else "none",
                error="No notifications"
            )
        
        html, _ = self.render_template("digest", {
            "notifications": [n.to_dict() for n in notifications],
            "frequency": frequency,
            "count": len(notifications)
        })
        
        subject = f"Your {frequency} digest - {len(notifications)} new notifications"
        return self.send_email(email, subject, html)
    
    # ============================================
    # معالجة الإشعارات
    # ============================================
    
    def process_queue(self, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
        """معالجة قائمة الانتظار"""
        if not self.redis:
            return 0
        
        processed = 0
        for _ in range(batch_size):
            data = self.redis.rpop("notifications:queue")
            if not data:
                break
            
            try:
                notification = Notification.from_json(data)
                self._send_notification(notification)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process notification: {e}")
                self.redis.lpush("notifications:failed", data)
        
        return processed
    
    def process_scheduled(self) -> int:
        """معالجة الإشعارات المجدولة"""
        if not self.redis:
            return 0
        
        now = utc_now().timestamp()
        data_list = self.redis.zrangebyscore("notifications:scheduled", 0, now)
        
        processed = 0
        for data in data_list:
            try:
                notification = Notification.from_json(data)
                self._send_notification(notification)
                self.redis.zrem("notifications:scheduled", data)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process scheduled notification: {e}")
        
        return processed
    
    def _send_notification(self, notification: Notification):
        """إرسال إشعار حسب قناته"""
        if notification.channel == NotificationChannel.EMAIL:
            # نحتاج البريد من user_id
            user = self._get_user(notification.user_id)
            if user and user.email:
                self.send_templated_email(user.email, notification.type, notification.data)
        elif notification.channel == NotificationChannel.PUSH:
            title = notification.subject or self.render_subject(notification.type, notification.data)
            body = notification.content or ""
            self.send_push(notification.user_id, title, body, notification.data, notification.priority)
        elif notification.channel == NotificationChannel.SMS:
            user = self._get_user(notification.user_id)
            if user and user.phone:
                self.send_sms(user.phone, notification.content or "")
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def _get_user(self, user_id: str) -> Optional[Any]:
        """جلب المستخدم - يجب override في الإنتاج"""
        # هذا مجرد stub - في الإنتاج نستخدم UserRepository
        return None
    
    def _get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """جلب تفضيلات المستخدم"""
        if not self.redis:
            return None
        
        data = self.redis.get(f"user:prefs:{user_id}")
        if data:
            d = json.loads(data)
            return UserPreferences(**d)
        return None
    
    def _get_channels_for_type(self, notification_type: NotificationType) -> List[NotificationChannel]:
        """تحديد القنوات المناسبة لنوع الإشعار"""
        channels_map = {
            NotificationType.NEW_MESSAGE: [NotificationChannel.PUSH, NotificationChannel.EMAIL],
            NotificationType.ADMIN_ALERT: [NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.SMS],
            NotificationType.PAYOUT_SENT: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        }
        return channels_map.get(notification_type, [NotificationChannel.EMAIL])
    
    def _record_metrics(self, channel: str, success: bool):
        """تسجيل الإحصائيات"""
        if not self.redis:
            return
        
        key = f"metrics:{channel}_{'sent' if success else 'failed'}"
        self.redis.incr(key)
    
    def should_notify(self, user_id: str, notification_type: NotificationType) -> bool:
        """التحقق من إمكانية الإرسال"""
        if not self.redis:
            return True
        
        # Cooldown
        cooldown = self._cooldowns.get(notification_type, DEFAULT_COOLDOWN_SECONDS)
        if cooldown > 0:
            last_key = f"last_notification:{user_id}:{notification_type.value}"
            last = self.redis.get(last_key)
            if last:
                last_time = datetime.fromisoformat(last)
                if utc_now() - last_time < timedelta(seconds=cooldown):
                    return False
        
        # Daily limit
        limit = self._daily_limits.get(notification_type, DEFAULT_DAILY_LIMIT)
        count_key = f"daily_count:{user_id}:{notification_type.value}:{utc_now().strftime('%Y%m%d')}"
        count = self.redis.get(count_key)
        if count and int(count) >= limit:
            return False
        
        # تحديث العدادات
        self.redis.setex(last_key, cooldown * 2, utc_now().isoformat())
        self.redis.incr(count_key)
        self.redis.expire(count_key, 86400)
        
        return True
    
    # ============================================
    # الصحة والمراقبة
    # ============================================
    
    def health_check(self) -> HealthStatus:
        """فحص صحة الخدمة"""
        email_available = False
        if self.email_provider:
            try:
                success, _ = self.email_provider.send("health@test.com", "Health Check", "<p>Test</p>")
                email_available = success
            except:
                pass
        
        return HealthStatus(
            status="healthy" if email_available else "degraded",
            email_provider=self.email_provider.name if self.email_provider else "none",
            email_available=email_available,
            push_available=self.push_service is not None,
            sms_available=self.sms_provider is not None,
            queue_size=self.redis.llen("notifications:queue") if self.redis else 0,
            retry_queue_size=self.redis.zcard("notifications:retry") if self.redis else 0,
            circuit_breaker_state=self.circuit_breaker.state.value
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات"""
        if not self.redis:
            return {}
        
        return {
            "emails_sent": int(self.redis.get("metrics:email_sent") or 0),
            "emails_failed": int(self.redis.get("metrics:email_failed") or 0),
            "push_sent": int(self.redis.get("metrics:push_sent") or 0),
            "push_failed": int(self.redis.get("metrics:push_failed") or 0),
            "sms_sent": int(self.redis.get("metrics:sms_sent") or 0),
            "queue_size": self.redis.llen("notifications:queue"),
            "scheduled_count": self.redis.zcard("notifications:scheduled"),
        }
    
    def __repr__(self) -> str:
        return f"<NotificationService email={bool(self.email_provider)} push={bool(self.push_service)}>"


__all__ = [
    "NotificationService",
    "NotificationType",
    "NotificationPriority",
    "NotificationChannel",
    "Notification",
    "NotificationResult",
    "UserPreferences",
    "HealthStatus",
    "SMTPEmailProvider",
    "SendGridProvider",
]
