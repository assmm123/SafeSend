"""
Reputation Service - SafeSend
خدمة السمعة - SafeSend

Manages user reputation, trust scores, badges, and post-deal reputation updates.
يدير سمعة المستخدم، درجات الثقة، الشارات، وتحديثات السمعة بعد الصفقات.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)

# Weight factors for trust score calculation
WEIGHT_RATING = 0.40
WEIGHT_DEALS = 0.25
WEIGHT_AGE = 0.10
WEIGHT_KYC = 0.10
WEIGHT_DISPUTES = 0.15

class ReputationService:
    """
    User reputation and trust score service.
    خدمة سمعة المستخدم ودرجة الثقة.
    
    Calculates trust scores from multiple weighted factors.
    يحسب درجات الثقة من عوامل متعددة موزونة.
    """
    
    def __init__(self):
        self._profiles: Dict[int, Dict[str, Any]] = {}
        self._reviews: Dict[int, List[Dict[str, Any]]] = {}
    
    # ============================================================
    # Reviews
    # ============================================================
    
    def add_review(self, deal_id: int, reviewer_id: int, reviewed_id: int, 
                   ratings: Dict[str, int], comment: str = '') -> Dict[str, Any]:
        """
        Add a review and update reputation.
        إضافة تقييم وتحديث السمعة.
        """
        if reviewed_id not in self._reviews:
            self._reviews[reviewed_id] = []
        
        overall = sum(ratings.values()) / len(ratings) if ratings else 0
        
        review = {
            'id': len(self._reviews[reviewed_id]) + 1,
            'deal_id': deal_id,
            'reviewer_id': reviewer_id,
            'reviewed_id': reviewed_id,
            'ratings': ratings,
            'overall': round(overall, 2),
            'comment': comment,
            'is_verified_purchase': True,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        self._reviews[reviewed_id].append(review)
        
        # Update trust score
        self.calculate_trust_score(reviewed_id)
        
        logger.info("reputation.review_added", reviewed_id=reviewed_id, overall=overall)
        return {'success': True, 'review': review}
    
    # ============================================================
    # Trust Score
    # ============================================================
    
    def calculate_trust_score(self, user_id: int) -> float:
        """
        Calculate weighted trust score (0-100).
        حساب درجة الثقة الموزونة (0-100).
        
        Factors:
        - Rating (40%): Average review rating
        - Deals (25%): Number of completed deals
        - Age (10%): Account age
        - KYC (10%): Verification status
        - Disputes (15%): Negative: dispute ratio
        """
        profile = self._get_profile(user_id)
        reviews = self._reviews.get(user_id, [])
        
        # Rating score (0-40)
        avg_rating = sum(r['overall'] for r in reviews) / len(reviews) if reviews else 0
        rating_score = min(40, (avg_rating / 5.0) * WEIGHT_RATING * 100)
        
        # Deals score (0-25)
        completed_deals = profile.get('completed_deals', 0)
        deals_score = min(25, (completed_deals / 100) * WEIGHT_DEALS * 100)
        
        # Account age score (0-10)
        created_at = profile.get('created_at')
        if created_at:
            days_old = (datetime.now(timezone.utc) - datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)).days
            age_score = min(10, (days_old / 365) * WEIGHT_AGE * 100)
        else:
            age_score = 0
        
        # KYC score (0-10)
        kyc_verified = profile.get('kyc_verified', False)
        two_factor = profile.get('two_factor_enabled', False)
        kyc_score = 0
        if kyc_verified:
            kyc_score += 7
        if two_factor:
            kyc_score += 3
        kyc_score = min(10, kyc_score)
        
        # Disputes score (0-15, negative impact)
        disputes = profile.get('disputes', 0)
        dispute_ratio = disputes / max(1, completed_deals)
        dispute_penalty = min(15, dispute_ratio * WEIGHT_DISPUTES * 100)
        dispute_score = max(0, 15 - dispute_penalty)
        
        total = round(rating_score + deals_score + age_score + kyc_score + dispute_score, 2)
        total = max(0, min(100, total))
        
        profile['trust_score'] = total
        profile['trust_score_breakdown'] = {
            'rating': round(rating_score, 2),
            'deals': round(deals_score, 2),
            'age': round(age_score, 2),
            'kyc': round(kyc_score, 2),
            'disputes': round(dispute_score, 2),
            'total': total
        }
        profile['last_calculated'] = datetime.now(timezone.utc).isoformat()
        
        logger.info("reputation.trust_score_calculated", user_id=user_id, score=total)
        return total
    
    # ============================================================
    # Badges
    # ============================================================
    
    def get_user_badges(self, user_id: int) -> List[str]:
        """
        Get user badges based on stats.
        شارات المستخدم حسب الإحصائيات.
        """
        profile = self._get_profile(user_id)
        reviews = self._reviews.get(user_id, [])
        badges = []
        
        avg_rating = sum(r['overall'] for r in reviews) / len(reviews) if reviews else 0
        deals = profile.get('completed_deals', 0)
        kyc = profile.get('kyc_verified', False)
        disputes = profile.get('disputes', 0)
        
        if deals >= 200 and avg_rating >= 4.9:
            badges.append('💎 Elite')
        elif deals >= 50 and avg_rating >= 4.5:
            badges.append('🥇 Expert')
        elif deals >= 10 and avg_rating >= 4.0:
            badges.append('🥈 Trusted')
        
        if kyc and profile.get('two_factor_enabled', False) and disputes == 0:
            badges.append('🛡️ Security Expert')
        
        if deals >= 100:
            badges.append('💰 Top Seller')
        
        if reviews and len(reviews) >= 50 and avg_rating >= 4.8:
            badges.append('⭐ Top Rated')
        
        return badges
    
    def check_badge_eligibility(self, user_id: int) -> List[str]:
        """
        Check which badges user is close to earning.
        فحص الشارات التي يقترب المستخدم من الحصول عليها.
        """
        profile = self._get_profile(user_id)
        reviews = self._reviews.get(user_id, [])
        eligible = []
        
        avg_rating = sum(r['overall'] for r in reviews) / len(reviews) if reviews else 0
        deals = profile.get('completed_deals', 0)
        kyc = profile.get('kyc_verified', False)
        
        current_badges = self.get_user_badges(user_id)
        
        if '💎 Elite' not in current_badges:
            if deals >= 150:
                eligible.append('💎 Elite (تحتاج 50 صفقة إضافية)')
            elif avg_rating >= 4.8:
                eligible.append('💎 Elite (تحتاج 200 صفقة)')
        
        if '🥇 Expert' not in current_badges:
            if deals >= 40:
                eligible.append('🥇 Expert (تحتاج 10 صفقات إضافية)')
        
        if '🛡️ Security Expert' not in current_badges and kyc:
            eligible.append('🛡️ Security Expert (فعل المصادقة الثنائية)')
        
        return eligible
    
    # ============================================================
    # Post-Deal Update
    # ============================================================
    
    def update_reputation_after_deal(self, deal_id: int, seller_id: int, 
                                      buyer_id: int, deal_amount: float) -> Dict[str, Any]:
        """
        Update reputation stats after deal completion.
        تحديث إحصائيات السمعة بعد إتمام الصفقة.
        """
        result = {'seller': None, 'buyer': None}
        
        # Update seller
        seller_profile = self._get_profile(seller_id)
        seller_profile['completed_deals'] = seller_profile.get('completed_deals', 0) + 1
        seller_profile['total_volume'] = seller_profile.get('total_volume', 0) + deal_amount
        seller_score = self.calculate_trust_score(seller_id)
        result['seller'] = {'new_score': seller_score}
        
        # Update buyer
        buyer_profile = self._get_profile(buyer_id)
        buyer_profile['total_buys'] = buyer_profile.get('total_buys', 0) + 1
        buyer_profile['total_spent'] = buyer_profile.get('total_spent', 0) + deal_amount
        buyer_score = self.calculate_trust_score(buyer_id)
        result['buyer'] = {'new_score': buyer_score}
        
        logger.info("reputation.deal_updated", deal_id=deal_id, 
                    seller_id=seller_id, buyer_id=buyer_id)
        
        return {'success': True, 'results': result}
    
    # ============================================================
    # Queries
    # ============================================================
    
    def get_reputation_breakdown(self, user_id: int) -> Dict[str, Any]:
        """Get detailed reputation breakdown. / تفصيل مكونات السمعة."""
        self.calculate_trust_score(user_id)
        profile = self._get_profile(user_id)
        return {
            'user_id': user_id,
            'trust_score': profile.get('trust_score', 0),
            'breakdown': profile.get('trust_score_breakdown', {}),
            'badges': self.get_user_badges(user_id),
            'completed_deals': profile.get('completed_deals', 0),
            'total_reviews': len(self._reviews.get(user_id, [])),
            'eligible_badges': self.check_badge_eligibility(user_id)
        }
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top rated users. / أفضل المستخدمين."""
        scored = []
        for uid in self._profiles:
            score = self.calculate_trust_score(uid)
            scored.append({'user_id': uid, 'trust_score': score})
        
        scored.sort(key=lambda x: x['trust_score'], reverse=True)
        return scored[:limit]
    
    def compare_users(self, user_id_1: int, user_id_2: int) -> Dict[str, Any]:
        """Compare two users' reputation. / مقارنة سمعة مستخدمين."""
        return {
            'user_1': self.get_reputation_breakdown(user_id_1),
            'user_2': self.get_reputation_breakdown(user_id_2)
        }
    
    def get_reputation_trend(self, user_id: int) -> str:
        """Get reputation trend direction. / اتجاه السمعة."""
        reviews = self._reviews.get(user_id, [])
        if len(reviews) < 2:
            return 'stable'
        
        recent = reviews[-5:]
        old = reviews[:-5] if len(reviews) > 5 else reviews[:len(reviews)//2]
        
        recent_avg = sum(r['overall'] for r in recent) / len(recent) if recent else 0
        old_avg = sum(r['overall'] for r in old) / len(old) if old else 0
        
        if recent_avg > old_avg + 0.2:
            return 'improving'
        elif recent_avg < old_avg - 0.2:
            return 'declining'
        return 'stable'
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _get_profile(self, user_id: int) -> Dict[str, Any]:
        """Get or create user reputation profile."""
        if user_id not in self._profiles:
            self._profiles[user_id] = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'completed_deals': 0, 'total_volume': 0,
                'total_buys': 0, 'total_spent': 0,
                'disputes': 0, 'kyc_verified': False,
                'two_factor_enabled': False, 'trust_score': 0
            }
        return self._profiles[user_id]
    
    def set_user_stats(self, user_id: int, stats: Dict[str, Any]) -> None:
        """Set user statistics manually. / تعيين إحصائيات المستخدم يدوياً."""
        profile = self._get_profile(user_id)
        profile.update(stats)
        self.calculate_trust_score(user_id)


reputation_service = ReputationService()

__all__ = ['ReputationService', 'reputation_service']
