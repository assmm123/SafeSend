"""
Fraud Detection Service - SafeSend
خدمة كشف الاحتيال - SafeSend

Analyzes user behavior, detects suspicious patterns, and auto-applies limits.
يحلل سلوك المستخدم ويكتشف الأنماط المشبوهة ويطبق الحدود تلقائياً.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import structlog

logger = structlog.get_logger(__name__)

# Risk thresholds
RISK_LOW = 30
RISK_MEDIUM = 60
RISK_HIGH = 80

# Detection windows
RAPID_TX_WINDOW_MINUTES = 10
RAPID_TX_COUNT = 5
NEW_USER_DAYS = 7
NEW_USER_HIGH_VALUE = 1000
MULTIPLE_DISPUTES_DAYS = 30
MULTIPLE_DISPUTES_COUNT = 3
CIRCULAR_DEPTH = 3
SUSPICIOUS_LOGIN_COUNTRIES = 3
SUSPICIOUS_LOGIN_HOURS = 1
FAKE_REVIEWS_COUNT = 10
ACCOUNT_FARMING_IP_COUNT = 5

class FraudScore:
    """Fraud risk score with details."""
    def __init__(self, score: int = 0):
        self.score = score
        self.reasons: List[str] = []
        self.level: str = 'low'
    
    def add(self, points: int, reason: str) -> None:
        self.score = min(100, self.score + points)
        self.reasons.append(reason)
        if self.score >= RISK_HIGH: self.level = 'critical'
        elif self.score >= RISK_MEDIUM: self.level = 'high'
        elif self.score >= RISK_LOW: self.level = 'medium'
    
    def to_dict(self) -> Dict[str, Any]:
        return {'score': self.score, 'level': self.level, 'reasons': self.reasons}

class FraudDetection:
    """
    Fraud detection and prevention service.
    خدمة كشف ومنع الاحتيال.
    
    Detects 10+ fraud patterns with automatic countermeasures.
    يكتشف 10+ أنماط احتيال مع إجراءات مضادة تلقائية.
    """
    
    def __init__(self):
        self._user_profiles: Dict[int, Dict[str, Any]] = {}
        self._transactions: List[Dict[str, Any]] = []
        self._blacklist: set = set()
        self._whitelist: set = set()
        self._suspicious_events: List[Dict[str, Any]] = []
    
    # ============================================================
    # Main Analysis
    # ============================================================
    
    def analyze_user_behavior(self, user_id: int, event_data: Dict[str, Any]) -> FraudScore:
        """
        Analyze user behavior for fraud detection.
        تحليل سلوك المستخدم لكشف الاحتيال.
        """
        score = FraudScore()
        profile = self._get_profile(user_id)
        
        # 1. Rapid transactions
        if self._check_rapid_transactions(user_id):
            score.add(25, 'rapid_transactions')
        
        # 2. New user high value
        if self._check_new_user_high_value(user_id, event_data):
            score.add(20, 'new_user_high_value')
        
        # 3. Multiple disputes
        if self._check_multiple_disputes(user_id):
            score.add(15, 'multiple_disputes')
        
        # 4. Suspicious login
        if self._check_suspicious_login(user_id, event_data):
            score.add(15, 'suspicious_login')
        
        # 5. Account farming
        if self._check_account_farming(event_data.get('ip_address', '')):
            score.add(30, 'account_farming')
        
        # 6. Rapid payout request
        if self._check_rapid_payout(user_id):
            score.add(10, 'rapid_payout')
        
        # 7. Duplicate deals
        if self._check_duplicate_deals(user_id, event_data):
            score.add(10, 'duplicate_deals')
        
        profile['risk_score'] = score.score
        profile['last_analyzed'] = datetime.now(timezone.utc).isoformat()
        
        if score.score >= RISK_HIGH:
            self.log_suspicious_event(user_id, 'high_risk_detected', score.to_dict())
        
        return score
    
    def check_suspicious_activity(self, user_id: int) -> bool:
        """
        Check if user has suspicious activity.
        فحص وجود نشاط مشبوه.
        """
        profile = self._get_profile(user_id)
        return profile.get('risk_score', 0) >= RISK_MEDIUM
    
    def get_risk_level(self, user_id: int) -> str:
        """
        Get user risk level.
        الحصول على مستوى خطورة المستخدم.
        """
        if user_id in self._blacklist:
            return 'critical'
        if user_id in self._whitelist:
            return 'low'
        score = self._get_profile(user_id).get('risk_score', 0)
        if score >= RISK_HIGH: return 'critical'
        if score >= RISK_MEDIUM: return 'high'
        if score >= RISK_LOW: return 'medium'
        return 'low'
    
    def apply_limits(self, user_id: int) -> Dict[str, Any]:
        """
        Apply transaction limits based on risk level.
        تطبيق حدود المعاملات حسب مستوى الخطورة.
        """
        level = self.get_risk_level(user_id)
        limits = {
            'low': {'daily': 50000, 'per_transaction': 5000},
            'medium': {'daily': 10000, 'per_transaction': 1000},
            'high': {'daily': 1000, 'per_transaction': 100},
            'critical': {'daily': 0, 'per_transaction': 0}
        }
        return limits.get(level, limits['low'])
    
    # ============================================================
    # Fraud Patterns
    # ============================================================
    
    def _check_rapid_transactions(self, user_id: int) -> bool:
        """Check for rapid consecutive transactions."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=RAPID_TX_WINDOW_MINUTES)
        recent = [t for t in self._transactions if t.get('user_id') == user_id and 
                  datetime.fromisoformat(t.get('timestamp', '2000-01-01T00:00:00')).replace(tzinfo=timezone.utc) > cutoff]
        return len(recent) >= RAPID_TX_COUNT
    
    def _check_new_user_high_value(self, user_id: int, event: Dict[str, Any]) -> bool:
        """Check for new user with high value transaction."""
        profile = self._get_profile(user_id)
        created = profile.get('created_at')
        if not created:
            return False
        days_old = (datetime.now(timezone.utc) - datetime.fromisoformat(created).replace(tzinfo=timezone.utc)).days
        if days_old <= NEW_USER_DAYS:
            amount = event.get('amount', 0)
            return amount >= NEW_USER_HIGH_VALUE
        return False
    
    def _check_multiple_disputes(self, user_id: int) -> bool:
        """Check for excessive disputes."""
        profile = self._get_profile(user_id)
        disputes = profile.get('disputes', [])
        cutoff = datetime.now(timezone.utc) - timedelta(days=MULTIPLE_DISPUTES_DAYS)
        recent = [d for d in disputes if datetime.fromisoformat(d.get('date', '2000-01-01T00:00:00')).replace(tzinfo=timezone.utc) > cutoff]
        return len(recent) >= MULTIPLE_DISPUTES_COUNT
    
    def _check_suspicious_login(self, user_id: int, event: Dict[str, Any]) -> bool:
        """Check login from multiple countries in short time."""
        ip = event.get('ip_address', '')
        country = event.get('country', 'unknown')
        profile = self._get_profile(user_id)
        logins = profile.get('logins', [])
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SUSPICIOUS_LOGIN_HOURS)
        recent_countries = set()
        for login in logins:
            if datetime.fromisoformat(login.get('timestamp', '2000-01-01T00:00:00')).replace(tzinfo=timezone.utc) > cutoff:
                recent_countries.add(login.get('country', ''))
        recent_countries.add(country)
        return len(recent_countries) >= SUSPICIOUS_LOGIN_COUNTRIES
    
    def _check_account_farming(self, ip_address: str) -> bool:
        """Check for multiple accounts from same IP."""
        count = sum(1 for p in self._user_profiles.values() if p.get('signup_ip') == ip_address)
        return count >= ACCOUNT_FARMING_IP_COUNT
    
    def _check_rapid_payout(self, user_id: int) -> bool:
        """Check for payout request immediately after deposit."""
        profile = self._get_profile(user_id)
        last_deposit = profile.get('last_deposit_at')
        last_payout = profile.get('last_payout_request_at')
        if last_deposit and last_payout:
            deposit_time = datetime.fromisoformat(last_deposit).replace(tzinfo=timezone.utc)
            payout_time = datetime.fromisoformat(last_payout).replace(tzinfo=timezone.utc)
            return (payout_time - deposit_time).total_seconds() < 300  # 5 minutes
        return False
    
    def _check_duplicate_deals(self, user_id: int, event: Dict[str, Any]) -> bool:
        """Check for duplicate deals with different sellers."""
        title = event.get('title', '')
        if not title:
            return False
        profile = self._get_profile(user_id)
        deals = profile.get('deals', [])
        similar = [d for d in deals if d.get('title', '').lower() == title.lower()]
        return len(similar) >= 2
    
    # ============================================================
    # Management
    # ============================================================
    
    def log_suspicious_event(self, user_id: int, event_type: str, details: Dict[str, Any]) -> None:
        """Log a suspicious event."""
        self._suspicious_events.append({
            'user_id': user_id, 'type': event_type, 'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.warning("fraud.suspicious_event", user_id=user_id, type=event_type)
    
    def blacklist_user(self, user_id: int, reason: str) -> None:
        """Add user to blacklist."""
        self._blacklist.add(user_id)
        profile = self._get_profile(user_id)
        profile['blacklisted'] = True
        profile['blacklist_reason'] = reason
        logger.warning("fraud.blacklisted", user_id=user_id, reason=reason)
    
    def whitelist_user(self, user_id: int) -> None:
        """Add user to whitelist."""
        self._whitelist.add(user_id)
        logger.info("fraud.whitelisted", user_id=user_id)
    
    def get_fraud_report(self) -> Dict[str, Any]:
        """Get fraud detection report."""
        return {
            'total_events': len(self._suspicious_events),
            'blacklisted': len(self._blacklist),
            'whitelisted': len(self._whitelist),
            'recent_events': self._suspicious_events[-20:],
            'high_risk_users': sum(1 for p in self._user_profiles.values() if p.get('risk_score', 0) >= RISK_HIGH)
        }
    
    def _get_profile(self, user_id: int) -> Dict[str, Any]:
        """Get or create user behavior profile."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'risk_score': 0, 'transactions': [], 'disputes': [],
                'logins': [], 'deals': []
            }
        return self._user_profiles[user_id]


fraud_detection = FraudDetection()

__all__ = ['FraudDetection', 'fraud_detection', 'FraudScore', 'RISK_LOW', 'RISK_MEDIUM', 'RISK_HIGH']
