"""
خدمة Push Notifications المتقدمة
Advanced Push Notification Service

دعم Web Push (VAPID) و FCM و APNs
- إدارة الاشتراكات
- تجميع الإشعارات
- تنظيف الاشتراكات المنتهية
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from tenacity import retry, stop_after_attempt, wait_exponential

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

class PushProvider:
    WEB_PUSH = "web_push"
    FCM = "fcm"
    APNS = "apns"


DEFAULT_VAPID_CLAIMS = {"sub": "mailto:support@safesend.com"}
DEFAULT_ICON = "/static/icon-192x192.png"
DEFAULT_BADGE = "/static/badge-72x72.png"
DEFAULT_TIMEOUT = 10


# ============================================
# Data Classes
# ============================================

@dataclass
class PushResult:
    """نتيجة إرسال Push"""
    success: bool
    user_id: str
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    endpoint: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "user_id": self.user_id,
            "provider": self.provider,
            "message_id": self.message_id,
            "error": self.error,
            "endpoint": self.endpoint,
        }


@dataclass
class BatchPushResult:
    """نتيجة إرسال دفعة"""
    total: int
    success: int
    failed: int
    results: List[PushResult] = field(default_factory=list)
    duration_ms: float = 0
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "duration_ms": self.duration_ms,
        }


@dataclass
class HealthStatus:
    """حالة صحة الخدمة"""
    status: str
    vapid_configured: bool
    fcm_configured: bool
    apns_configured: bool
    total_subscriptions: int
    circuit_breaker_state: str


# ============================================
# Exceptions
# ============================================

class PushError(Exception):
    pass


class WebPushError(PushError):
    pass


class FCMError(PushError):
    pass


# ============================================
# Push Service
# ============================================

class PushService:
    """خدمة Push Notifications المتقدمة"""
    
    # قوالب الإشعارات
    NOTIFICATION_TEMPLATES = {
        "new_message": {"title": "New message from {sender}", "body": "{preview}"},
        "deal_created": {"title": "New deal created", "body": "{title}"},
        "payment_received": {"title": "Payment received! 💰", "body": "Your payment of {amount} has been received"},
        "payout_sent": {"title": "Payout sent! 🎉", "body": "Your payout of {amount} has been sent"},
        "work_delivered": {"title": "Work delivered", "body": "Seller delivered work for {title}"},
        "dispute_opened": {"title": "Dispute opened", "body": "A dispute has been opened for {title}"},
    }
    
    def __init__(
        self,
        vapid_private_key: Optional[str] = None,
        vapid_public_key: Optional[str] = None,
        vapid_claims: Optional[dict] = None,
        fcm_server_key: Optional[str] = None,
        apns_cert_path: Optional[str] = None,
        redis_client: Any = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_claims = vapid_claims or DEFAULT_VAPID_CLAIMS
        self.fcm_server_key = fcm_server_key
        self.apns_cert_path = apns_cert_path
        self.redis = redis_client
        
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="push_service", failure_threshold=3, timeout=30.0
        )
        
        logger.info(f"PushService initialized: web_push={bool(vapid_private_key)} fcm={bool(fcm_server_key)}")
    
    # ============================================
    # دوال VAPID المساعدة
    # ============================================
    
    @staticmethod
    def generate_vapid_keys() -> tuple:
        """توليد مفاتيح VAPID جديدة"""
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from base64 import urlsafe_b64encode
            
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key = private_key.public_key()
            
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            
            return (
                urlsafe_b64encode(private_bytes).decode('utf-8').strip('='),
                urlsafe_b64encode(public_bytes).decode('utf-8').strip('=')
            )
        except Exception as e:
            logger.error(f"Failed to generate VAPID keys: {e}")
            raise PushError(f"VAPID key generation failed: {e}")
    
    # ============================================
    # Web Push
    # ============================================
    
    def send_web_push(self, subscription: dict, payload: dict) -> tuple:
        """إرسال Web Push باستخدام VAPID"""
        if not self.vapid_private_key:
            return False, "VAPID not configured"
        
        try:
            from pywebpush import webpush, WebPushException
            
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
                timeout=DEFAULT_TIMEOUT
            )
            
            return True, None
            
        except ImportError:
            return False, "pywebpush not installed"
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                self.remove_subscription_by_endpoint(subscription.get('endpoint'))
                return False, "Subscription expired"
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    # ============================================
    # FCM (Firebase Cloud Messaging)
    # ============================================
    
    def send_fcm(self, token: str, title: str, body: str, data: Optional[dict] = None) -> tuple:
        """إرسال عبر FCM"""
        if not self.fcm_server_key:
            return False, "FCM not configured"
        
        try:
            import requests
            
            headers = {
                'Authorization': f'key={self.fcm_server_key}',
                'Content-Type': 'application/json'
            }
            
            message = {
                'to': token,
                'notification': {'title': title, 'body': body},
                'data': data or {}
            }
            
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                headers=headers,
                json=message,
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('failure') == 1:
                    error = result.get('results', [{}])[0].get('error')
                    if error == 'NotRegistered':
                        self.remove_fcm_token(token)
                    return False, error
                return result.get('success', 0) > 0, None
            
            return False, f"HTTP {response.status_code}"
            
        except ImportError:
            return False, "requests not installed"
        except Exception as e:
            return False, str(e)
    
    # ============================================
    # إرسال موحد
    # ============================================
    
    def send_to_user(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        require_interaction: bool = False
    ) -> List[PushResult]:
        """إرسال إشعار لمستخدم عبر جميع أجهزته"""
        results = []
        
        payload = {
            'title': title,
            'body': body,
            'icon': DEFAULT_ICON,
            'badge': DEFAULT_BADGE,
            'data': data or {},
            'requireInteraction': require_interaction
        }
        
        if url:
            payload['data']['url'] = url
        if image_url:
            payload['image'] = image_url
        
        # Web Push
        web_subs = self.get_user_subscriptions(user_id)
        for sub in web_subs:
            success, error = self.send_web_push(sub, payload)
            results.append(PushResult(
                success=success, user_id=user_id, provider=PushProvider.WEB_PUSH,
                error=error, endpoint=sub.get('endpoint')
            ))
        
        # FCM
        fcm_tokens = self.get_user_fcm_tokens(user_id)
        for token in fcm_tokens:
            success, error = self.send_fcm(token, title, body, data)
            results.append(PushResult(
                success=success, user_id=user_id, provider=PushProvider.FCM,
                error=error
            ))
        
        self._record_metrics("sent", len([r for r in results if r.success]))
        self._record_metrics("failed", len([r for r in results if not r.success]))
        
        return results
    
    def send_to_multiple(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        data: Optional[dict] = None,
        max_workers: int = 10
    ) -> BatchPushResult:
        """إرسال لعدة مستخدمين بالتوازي"""
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.send_to_user, uid, title, body, data): uid
                for uid in user_ids
            }
            
            for future in futures:
                try:
                    user_results = future.result(timeout=30)
                    results.extend(user_results)
                except Exception as e:
                    uid = futures[future]
                    results.append(PushResult(
                        success=False, user_id=uid, provider="unknown", error=str(e)
                    ))
        
        success_count = len([r for r in results if r.success])
        
        return BatchPushResult(
            total=len(user_ids),
            success=success_count,
            failed=len(user_ids) - success_count,
            results=results,
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def broadcast_to_all(self, title: str, body: str, data: Optional[dict] = None) -> BatchPushResult:
        """بث عام لجميع المستخدمين"""
        user_ids = self._get_all_users_with_subscriptions()
        return self.send_to_multiple(user_ids, title, body, data)
    
    # ============================================
    # قوالب الإشعارات
    # ============================================
    
    def send_templated(
        self,
        user_id: str,
        template_name: str,
        context: dict,
        url: Optional[str] = None
    ) -> List[PushResult]:
        """إرسال إشعار باستخدام قالب"""
        template = self.NOTIFICATION_TEMPLATES.get(template_name, {})
        title = template.get("title", "").format(**context)
        body = template.get("body", "").format(**context)
        
        data = {"template": template_name, **context}
        if url:
            data["url"] = url
        
        return self.send_to_user(user_id, title, body, data, url=url)
    
    # ============================================
    # إدارة الاشتراكات
    # ============================================
    
    def save_subscription(self, user_id: str, subscription: dict) -> bool:
        """حفظ اشتراك Web Push"""
        if not self.redis:
            return False
        
        if not self.validate_subscription(subscription):
            return False
        
        key = f"push:user:{user_id}"
        endpoint = subscription['endpoint']
        
        sub_data = {
            'endpoint': endpoint,
            'keys': subscription.get('keys', {}),
            'created_at': utc_now().isoformat()
        }
        
        self.redis.hset(key, endpoint, json.dumps(sub_data))
        self.redis.set(f"push:endpoint:{endpoint}", user_id)
        
        logger.info(f"Subscription saved for user {user_id}")
        return True
    
    def save_fcm_token(self, user_id: str, token: str, device_info: Optional[dict] = None) -> bool:
        """حفظ FCM token"""
        if not self.redis:
            return False
        
        key = f"fcm:user:{user_id}"
        token_data = {
            'token': token,
            'device': device_info or {},
            'created_at': utc_now().isoformat()
        }
        
        self.redis.hset(key, token, json.dumps(token_data))
        self.redis.set(f"fcm:token:{token}", user_id)
        
        return True
    
    def get_user_subscriptions(self, user_id: str) -> List[dict]:
        """جلب اشتراكات Web Push للمستخدم"""
        if not self.redis:
            return []
        
        key = f"push:user:{user_id}"
        data = self.redis.hgetall(key)
        return [json.loads(v) for v in data.values()]
    
    def get_user_fcm_tokens(self, user_id: str) -> List[str]:
        """جلب FCM tokens للمستخدم"""
        if not self.redis:
            return []
        
        key = f"fcm:user:{user_id}"
        data = self.redis.hgetall(key)
        tokens = []
        for v in data.values():
            token_data = json.loads(v)
            tokens.append(token_data['token'])
        return tokens
    
    def remove_subscription(self, user_id: str, endpoint: str) -> bool:
        """حذف اشتراك Web Push"""
        if not self.redis:
            return False
        
        key = f"push:user:{user_id}"
        self.redis.hdel(key, endpoint)
        self.redis.delete(f"push:endpoint:{endpoint}")
        
        return True
    
    def remove_subscription_by_endpoint(self, endpoint: str) -> bool:
        """حذف اشتراك باستخدام endpoint"""
        if not self.redis:
            return False
        
        user_id = self.redis.get(f"push:endpoint:{endpoint}")
        if user_id:
            return self.remove_subscription(user_id, endpoint)
        return False
    
    def remove_fcm_token(self, token: str) -> bool:
        """حذف FCM token"""
        if not self.redis:
            return False
        
        user_id = self.redis.get(f"fcm:token:{token}")
        if user_id:
            key = f"fcm:user:{user_id}"
            self.redis.hdel(key, token)
        
        self.redis.delete(f"fcm:token:{token}")
        return True
    
    def validate_subscription(self, subscription: dict) -> bool:
        """التحقق من صحة الاشتراك"""
        required = ['endpoint', 'keys']
        if not all(k in subscription for k in required):
            return False
        
        keys = subscription.get('keys', {})
        if not all(k in keys for k in ['p256dh', 'auth']):
            return False
        
        return True
    
    # ============================================
    # تنظيف
    # ============================================
    
    def cleanup_expired_subscriptions(self) -> int:
        """تنظيف الاشتراكات المنتهية"""
        if not self.redis:
            return 0
        
        removed = 0
        endpoints = self.redis.keys("push:endpoint:*")
        
        for endpoint_key in endpoints:
            endpoint = endpoint_key.decode().split(':')[-1]
            user_id = self.redis.get(endpoint_key)
            
            if user_id:
                key = f"push:user:{user_id}"
                sub_data = self.redis.hget(key, endpoint)
                
                if sub_data:
                    try:
                        sub = json.loads(sub_data)
                        success, error = self.send_web_push(sub, {'ping': True})
                        if not success and 'expired' in str(error).lower():
                            self.remove_subscription(user_id, endpoint)
                            removed += 1
                    except Exception:
                        pass
        
        return removed
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def _get_all_users_with_subscriptions(self) -> List[str]:
        """جلب جميع المستخدمين الذين لديهم اشتراكات"""
        if not self.redis:
            return []
        
        users = set()
        for key in self.redis.keys("push:user:*"):
            user_id = key.decode().split(':')[-1]
            users.add(user_id)
        
        return list(users)
    
    def _count_all_subscriptions(self) -> int:
        """عدد جميع الاشتراكات"""
        if not self.redis:
            return 0
        
        count = 0
        for key in self.redis.keys("push:user:*"):
            count += self.redis.hlen(key)
        
        return count
    
    def _record_metrics(self, metric: str, value: int):
        """تسجيل الإحصائيات"""
        if self.redis:
            self.redis.incrby(f"metrics:push:{metric}", value)
    
    # ============================================
    # الصحة والمراقبة
    # ============================================
    
    def health_check(self) -> HealthStatus:
        """فحص صحة الخدمة"""
        return HealthStatus(
            status="healthy" if self.vapid_private_key or self.fcm_server_key else "degraded",
            vapid_configured=bool(self.vapid_private_key),
            fcm_configured=bool(self.fcm_server_key),
            apns_configured=bool(self.apns_cert_path),
            total_subscriptions=self._count_all_subscriptions(),
            circuit_breaker_state=self.circuit_breaker.state.value
        )
    
    def get_metrics(self) -> dict:
        """الحصول على إحصائيات"""
        if not self.redis:
            return {}
        
        return {
            "total_subscriptions": self._count_all_subscriptions(),
            "active_users": len(self._get_all_users_with_subscriptions()),
            "web_push_sent": int(self.redis.get("metrics:push:sent") or 0),
            "web_push_failed": int(self.redis.get("metrics:push:failed") or 0),
            "vapid_configured": bool(self.vapid_private_key),
            "fcm_configured": bool(self.fcm_server_key),
        }
    
    def __repr__(self) -> str:
        return f"<PushService web_push={bool(self.vapid_private_key)} fcm={bool(self.fcm_server_key)}>"


__all__ = [
    "PushService",
    "PushProvider",
    "PushResult",
    "BatchPushResult",
    "HealthStatus",
    "PushError",
    "WebPushError",
    "FCMError",
]
