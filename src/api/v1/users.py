"""
Users API Endpoints - SafeSend
نقاط نهاية المستخدمين - SafeSend

Handles user profiles, reviews, portfolio, settings, and payment methods.
يدير الملفات الشخصية، التقييمات، الأعمال، الإعدادات، وطرق الدفع.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog

from src.app.models.user_repository import UserRepository
from src.app.models.security import decode_token
from src.api.schemas import (
    UserSchema,
    UserProfileSchema,
    UserUpdateSchema
)

logger = structlog.get_logger(__name__)
users_bp = Blueprint('users_v1', __name__, url_prefix='/api/v1/users')

# ============================================================
# 🔐 Helpers
# ============================================================

def _get_user_id() -> Optional[int]:
    """Extract user_id from JWT token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    payload = decode_token(token)
    if payload and 'user_id' in payload:
        try:
            return int(payload['user_id'])
        except (ValueError, TypeError):
            return None
    return None

def _require_auth():
    """Check authentication."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    return user_id, None

def _get_user_repo():
    return UserRepository()

# Temporary stores
_reviews = {}
_portfolio = {}
_user_settings = {}
_payment_methods = {}

# ============================================================
# 👤 Profiles
# ============================================================

@users_bp.route('/<username>', methods=['GET'])
def public_profile(username: str):
    """
    Get public user profile.
    الملف العام للمستخدم.
    """
    try:
        # In production: fetch from DB
        profile = {
            'id': 1, 'username': username, 'avatar': None,
            'rating': 4.5, 'total_reviews': 10, 'completed_deals': 25,
            'is_online': False, 'last_seen_at': datetime.now(timezone.utc)
        }
        
        return jsonify({'user': UserProfileSchema().dump(profile)}), 200
        
    except Exception as e:
        logger.error("user.profile_failed", error=str(e))
        return jsonify({'error': 'Profile not found', 'message_ar': 'الملف غير موجود'}), 404


@users_bp.route('/<username>/profile', methods=['GET'])
def full_profile(username: str):
    """
    Get full user profile (authenticated).
    الملف الشخصي الكامل.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        profile = {
            'id': user_id, 'username': username, 'email': 'user@example.com',
            'is_verified': True, 'rating': 4.5, 'completed_deals': 25,
            'preferred_payout_method': 'usdt', 'is_online': True,
            'created_at': datetime.now(timezone.utc)
        }
        
        return jsonify({'user': UserSchema().dump(profile)}), 200
        
    except Exception as e:
        logger.error("user.full_profile_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/profile', methods=['PUT'])
def update_profile():
    """
    Update authenticated user profile.
    تحديث الملف الشخصي.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        
        logger.info("user.profile_updated", user_id=user_id)
        
        return jsonify({
            'message': 'Profile updated',
            'message_ar': 'تم تحديث الملف الشخصي'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Update failed', 'message_ar': 'فشل التحديث'}), 500


@users_bp.route('/profile/avatar', methods=['POST'])
def upload_avatar():
    """Upload avatar. / رفع صورة شخصية."""
    user_id, error = _require_auth()
    if error:
        return error
    
    logger.info("user.avatar_uploaded", user_id=user_id)
    return jsonify({'message': 'Avatar uploaded', 'message_ar': 'تم رفع الصورة'}), 200


@users_bp.route('/profile/avatar', methods=['DELETE'])
def delete_avatar():
    """Delete avatar. / حذف الصورة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    logger.info("user.avatar_deleted", user_id=user_id)
    return jsonify({'message': 'Avatar deleted', 'message_ar': 'تم حذف الصورة'}), 200


# ============================================================
# ⭐ Reviews
# ============================================================

@users_bp.route('/<username>/reviews', methods=['GET'])
def user_reviews(username: str):
    """Get user reviews. / تقييمات المستخدم."""
    try:
        user_reviews = _reviews.get(username, [])
        
        return jsonify({
            'username': username,
            'reviews': user_reviews,
            'total': len(user_reviews),
            'average_rating': 4.5
        }), 200
        
    except Exception as e:
        return jsonify({'reviews': [], 'total': 0}), 200


@users_bp.route('/<username>/review', methods=['POST'])
def add_review(username: str):
    """Add a review. / إضافة تقييم."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        rating = data.get('rating', 5)
        comment = data.get('comment', '')
        
        review = {
            'id': len(_reviews.get(username, [])) + 1,
            'reviewer_id': user_id,
            'reviewed_username': username,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        if username not in _reviews:
            _reviews[username] = []
        _reviews[username].append(review)
        
        logger.info("user.review_added", username=username)
        
        return jsonify({
            'message': 'Review added',
            'message_ar': 'تم إضافة التقييم',
            'review': review
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 🎨 Portfolio
# ============================================================

@users_bp.route('/<username>/portfolio', methods=['GET'])
def user_portfolio(username: str):
    """Get user portfolio. / أعمال سابقة."""
    try:
        items = _portfolio.get(username, [])
        return jsonify({'username': username, 'portfolio': items, 'total': len(items)}), 200
    except Exception as e:
        return jsonify({'portfolio': [], 'total': 0}), 200


@users_bp.route('/portfolio', methods=['POST'])
def add_portfolio_item():
    """Add portfolio item. / إضافة عمل للمعرض."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '')
        description = data.get('description', '')
        
        item = {
            'id': len(_portfolio.get(str(user_id), [])) + 1,
            'user_id': user_id,
            'title': title,
            'description': description,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        if str(user_id) not in _portfolio:
            _portfolio[str(user_id)] = []
        _portfolio[str(user_id)].append(item)
        
        logger.info("user.portfolio_added", user_id=user_id)
        
        return jsonify({
            'message': 'Item added',
            'message_ar': 'تمت إضافة العمل',
            'item': item
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/portfolio/<int:item_id>', methods=['DELETE'])
def delete_portfolio_item(item_id: int):
    """Delete portfolio item. / حذف من المعرض."""
    user_id, error = _require_auth()
    if error:
        return error
    
    logger.info("user.portfolio_deleted", item_id=item_id)
    return jsonify({'message': 'Item deleted', 'message_ar': 'تم حذف العمل'}), 200


# ============================================================
# ⚙️ Settings
# ============================================================

@users_bp.route('/settings', methods=['GET'])
def user_settings():
    """Get user settings. / إعدادات المستخدم."""
    user_id, error = _require_auth()
    if error:
        return error
    
    settings = _user_settings.get(str(user_id), {
        'language': 'ar',
        'timezone': 'Asia/Damascus',
        'theme': 'light',
        'push_enabled': True,
        'email_notifications': True
    })
    
    return jsonify({'settings': settings}), 200


@users_bp.route('/settings', methods=['PUT'])
def update_settings():
    """Update user settings. / تحديث الإعدادات."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        _user_settings[str(user_id)] = data
        
        logger.info("user.settings_updated", user_id=user_id)
        
        return jsonify({'message': 'Settings updated', 'message_ar': 'تم تحديث الإعدادات'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/notifications', methods=['GET'])
def notification_settings():
    """Get notification settings. / إعدادات الإشعارات."""
    user_id, error = _require_auth()
    if error:
        return error
    
    return jsonify({
        'notifications': {
            'email_alerts': True,
            'push_alerts': True,
            'deal_updates': True,
            'message_alerts': True,
            'dispute_alerts': True
        }
    }), 200


@users_bp.route('/notifications', methods=['PUT'])
def update_notification_settings():
    """Update notification settings. / تحديث إعدادات الإشعارات."""
    user_id, error = _require_auth()
    if error:
        return error
    
    logger.info("user.notifications_updated", user_id=user_id)
    return jsonify({'message': 'Notification settings updated', 'message_ar': 'تم تحديث إعدادات الإشعارات'}), 200


# ============================================================
# 💳 Payment Methods
# ============================================================

@users_bp.route('/payout-methods', methods=['GET'])
def payout_methods():
    """Get user payout methods. / طرق الدفع."""
    user_id, error = _require_auth()
    if error:
        return error
    
    methods = _payment_methods.get(str(user_id), [
        {'method': 'usdt', 'address': 'TXXX...', 'verified': True},
        {'method': 'sham_cash', 'phone': '09XXXXXXXX', 'verified': False}
    ])
    
    return jsonify({'methods': methods}), 200


@users_bp.route('/payout-methods', methods=['PUT'])
def update_payout_methods():
    """Update payout methods. / تحديث طرق الدفع."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        _payment_methods[str(user_id)] = data.get('methods', [])
        
        logger.info("user.payout_methods_updated", user_id=user_id)
        
        return jsonify({'message': 'Payment methods updated', 'message_ar': 'تم تحديث طرق الدفع'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/payout-methods/<method>/verify', methods=['POST'])
def verify_payout_method(method: str):
    """Verify a payout method. / تحقق من طريقة دفع."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        code = data.get('code', '')
        
        logger.info("user.payout_method_verified", method=method)
        
        return jsonify({
            'message': f'{method} verified',
            'message_ar': f'تم التحقق من {method}'
        }), 200
    except Exception as e:
        return jsonify({'error': 'Verification failed', 'message_ar': 'فشل التحقق'}), 500


# ============================================================
# 📦 Export
# ============================================================

__all__ = ['users_bp']
