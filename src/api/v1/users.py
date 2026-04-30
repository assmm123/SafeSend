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

from src.app.models.database import get_db
from src.app.models.user import User
from src.app.models.user_repository import UserRepository, get_user_repo
from src.app.models.file import File, FileStatus
from src.models.review import Review
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
    return get_user_repo()

# ============================================================
# 👤 Profiles
# ============================================================

@users_bp.route('/<username>', methods=['GET'])
def public_profile(username: str):
    """
    Get public user profile from database.
    الملف العام للمستخدم.
    """
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            db.close()
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        # Count reviews
        review_count = db.query(Review).filter(Review.reviewed_id == user.id).count()
        
        # Calculate average rating
        reviews = db.query(Review).filter(Review.reviewed_id == user.id).all()
        if reviews:
            avg_rating = sum(
                (r.communication_rating + r.quality_rating + r.speed_rating + r.accuracy_rating) / 4
                for r in reviews
            ) / len(reviews)
        else:
            avg_rating = 0
        
        # Count completed deals
        from src.app.models.deal import Deal
        completed_deals = db.query(Deal).filter(
            Deal.status == 'completed',
            (Deal.buyer_id == user.id) | (Deal.seller_id == user.id)
        ).count()
        
        db.close()
        
        profile = {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'location': user.location,
            'rating': round(avg_rating, 1),
            'total_reviews': review_count,
            'completed_deals': completed_deals,
            'is_online': False,
            'last_seen_at': user.last_activity_at.isoformat() if user.last_activity_at else None
        }
        
        return jsonify({'user': UserProfileSchema().dump(profile)}), 200
        
    except Exception as e:
        logger.error("user.profile_failed", error=str(e))
        return jsonify({'error': 'Profile not found', 'message_ar': 'الملف غير موجود'}), 404


@users_bp.route('/<username>/profile', methods=['GET'])
def full_profile(username: str):
    """
    Get full user profile (authenticated) from database.
    الملف الشخصي الكامل.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        db = next(get_db())
        review_count = db.query(Review).filter(Review.reviewed_id == user.id).count()
        db.close()
        
        profile = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'location': user.location,
            'website': user.website,
            'is_verified': user.is_verified,
            'is_2fa_enabled': user.is_2fa_enabled,
            'rating': 4.5,  # Calculate from reviews
            'total_reviews': review_count,
            'completed_deals': 0,  # Calculate from deals
            'preferred_payout_method': user.get_preference('payout_method', 'usdt') if user.preferences else 'usdt',
            'is_online': True,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }
        
        return jsonify({'user': UserSchema().dump(profile)}), 200
        
    except Exception as e:
        logger.error("user.full_profile_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/profile', methods=['PUT'])
def update_profile():
    """
    Update authenticated user profile in database.
    تحديث الملف الشخصي.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        allowed_fields = ['full_name', 'phone', 'bio', 'location', 'website']
        
        update_data = {}
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'error': 'No valid fields', 'message_ar': 'لا توجد حقول صالحة'}), 400
        
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        repo.update(user, update_data)
        
        logger.info("user.profile_updated", user_id=user_id)
        
        return jsonify({
            'message': 'Profile updated',
            'message_ar': 'تم تحديث الملف الشخصي'
        }), 200
        
    except Exception as e:
        logger.error("user.profile_update_failed", error=str(e))
        return jsonify({'error': 'Update failed', 'message_ar': 'فشل التحديث'}), 500


@users_bp.route('/profile/avatar', methods=['POST'])
def upload_avatar():
    """Upload avatar. / رفع صورة شخصية."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file', 'message_ar': 'لا يوجد ملف'}), 400
        
        file = request.files['avatar']
        if not file.filename:
            return jsonify({'error': 'Empty file', 'message_ar': 'ملف فارغ'}), 400
        
        import os, uuid
        upload_dir = os.path.join('uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'png'
        filename = f"{user_id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        avatar_url = f"/uploads/avatars/{filename}"
        
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        if user:
            repo.update(user, {'avatar_url': avatar_url})
        
        logger.info("user.avatar_uploaded", user_id=user_id)
        
        return jsonify({
            'message': 'Avatar uploaded',
            'message_ar': 'تم رفع الصورة',
            'avatar_url': avatar_url
        }), 200
        
    except Exception as e:
        logger.error("user.avatar_upload_failed", error=str(e))
        return jsonify({'error': 'Upload failed', 'message_ar': 'فشل الرفع'}), 500


@users_bp.route('/profile/avatar', methods=['DELETE'])
def delete_avatar():
    """Delete avatar. / حذف الصورة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        if user and user.avatar_url:
            repo.update(user, {'avatar_url': None})
        
        logger.info("user.avatar_deleted", user_id=user_id)
        return jsonify({'message': 'Avatar deleted', 'message_ar': 'تم حذف الصورة'}), 200
        
    except Exception as e:
        logger.error("user.avatar_delete_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# ⭐ Reviews - Real Database
# ============================================================

@users_bp.route('/<username>/reviews', methods=['GET'])
def user_reviews(username: str):
    """Get user reviews from database. / تقييمات المستخدم."""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            db.close()
            return jsonify({'reviews': [], 'total': 0}), 200
        
        reviews = db.query(Review).filter(Review.reviewed_id == user.id).order_by(Review.created_at.desc()).all()
        
        result = []
        total_rating = 0
        for r in reviews:
            reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
            overall = (r.communication_rating + r.quality_rating + r.speed_rating + r.accuracy_rating) / 4
            total_rating += overall
            
            result.append({
                'id': r.id,
                'reviewer_name': reviewer.username if reviewer else 'مستخدم',
                'reviewer_id': r.reviewer_id,
                'communication_rating': r.communication_rating,
                'quality_rating': r.quality_rating,
                'speed_rating': r.speed_rating,
                'accuracy_rating': r.accuracy_rating,
                'comment': r.comment or '',
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        
        avg_rating = round(total_rating / len(result), 1) if result else 0
        
        db.close()
        return jsonify({
            'username': username,
            'reviews': result,
            'total': len(result),
            'average_rating': avg_rating
        }), 200
        
    except Exception as e:
        logger.error("user.reviews_failed", error=str(e))
        return jsonify({'reviews': [], 'total': 0, 'average_rating': 0}), 200


@users_bp.route('/<username>/review', methods=['POST'])
def add_review(username: str):
    """Add a review to database. / إضافة تقييم."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        
        communication_rating = data.get('communication_rating', data.get('rating', 5))
        quality_rating = data.get('quality_rating', data.get('rating', 5))
        speed_rating = data.get('speed_rating', data.get('rating', 5))
        accuracy_rating = data.get('accuracy_rating', data.get('rating', 5))
        comment = data.get('comment', '')
        
        db = next(get_db())
        reviewed_user = db.query(User).filter(User.username == username).first()
        
        if not reviewed_user:
            db.close()
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        if reviewed_user.id == user_id:
            db.close()
            return jsonify({'error': 'Cannot review yourself', 'message_ar': 'لا يمكن تقييم نفسك'}), 400
        
        # Check for duplicate review
        existing = db.query(Review).filter(
            Review.reviewer_id == user_id,
            Review.reviewed_id == reviewed_user.id
        ).first()
        
        if existing:
            db.close()
            return jsonify({'error': 'Already reviewed', 'message_ar': 'تم التقييم مسبقاً'}), 409
        
        review = Review(
            reviewer_id=user_id,
            reviewed_id=reviewed_user.id,
            communication_rating=communication_rating,
            quality_rating=quality_rating,
            speed_rating=speed_rating,
            accuracy_rating=accuracy_rating,
            comment=comment
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        
        review_id = review.id
        db.close()
        
        logger.info("user.review_added", username=username, review_id=review_id)
        
        return jsonify({
            'message': 'Review added',
            'message_ar': 'تم إضافة التقييم',
            'review': {
                'id': review_id,
                'reviewer_id': user_id,
                'reviewed_username': username,
                'communication_rating': communication_rating,
                'quality_rating': quality_rating,
                'speed_rating': speed_rating,
                'accuracy_rating': accuracy_rating,
                'comment': comment,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error("user.review_add_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 🎨 Portfolio - Uses File model
# ============================================================

@users_bp.route('/<username>/portfolio', methods=['GET'])
def user_portfolio(username: str):
    """Get user portfolio from database. / أعمال سابقة."""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            db.close()
            return jsonify({'portfolio': [], 'total': 0}), 200
        
        files = db.query(File).filter(
            File.uploaded_by == user.id,
            File.status.in_([FileStatus.READY, FileStatus.UPLOADING])
        ).order_by(File.created_at.desc()).all()
        
        result = []
        for f in files:
            result.append({
                'id': f.id,
                'title': f.original_name,
                'description': f.mime_type,
                'image_url': f"/uploads/{f.storage_path}" if f.storage_path else None,
                'created_at': f.created_at.isoformat() if f.created_at else None
            })
        
        db.close()
        return jsonify({
            'username': username,
            'portfolio': result,
            'total': len(result)
        }), 200
        
    except Exception as e:
        logger.error("user.portfolio_failed", error=str(e))
        return jsonify({'portfolio': [], 'total': 0}), 200


@users_bp.route('/portfolio', methods=['POST'])
def add_portfolio_item():
    """Add portfolio item to database. / إضافة عمل للمعرض."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '')
        description = data.get('description', '')
        image_url = data.get('image_url', '')
        
        if not title:
            return jsonify({'error': 'Title required', 'message_ar': 'العنوان مطلوب'}), 400
        
        db = next(get_db())
        new_file = File(
            original_name=title,
            file_size=0,
            mime_type='portfolio/item',
            storage_path=image_url if image_url else None,
            status=FileStatus.READY,
            uploaded_by=user_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        item_id = new_file.id
        db.close()
        
        logger.info("user.portfolio_added", user_id=user_id, item_id=item_id)
        
        return jsonify({
            'message': 'Item added',
            'message_ar': 'تمت إضافة العمل',
            'item': {
                'id': item_id,
                'user_id': user_id,
                'title': title,
                'description': description,
                'image_url': image_url,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error("user.portfolio_add_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/portfolio/<int:item_id>', methods=['DELETE'])
def delete_portfolio_item(item_id: int):
    """Delete portfolio item from database. / حذف من المعرض."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == item_id, File.uploaded_by == user_id).first()
        
        if not file_record:
            db.close()
            return jsonify({'error': 'Item not found', 'message_ar': 'العمل غير موجود'}), 404
        
        db.delete(file_record)
        db.commit()
        db.close()
        
        logger.info("user.portfolio_deleted", item_id=item_id, user_id=user_id)
        return jsonify({'message': 'Item deleted', 'message_ar': 'تم حذف العمل'}), 200
        
    except Exception as e:
        logger.error("user.portfolio_delete_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# ⚙️ Settings - From user.preferences
# ============================================================

@users_bp.route('/settings', methods=['GET'])
def user_settings():
    """Get user settings from database. / إعدادات المستخدم."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        settings = {
            'language': user.get_preference('language', 'ar'),
            'timezone': user.get_preference('timezone', 'Asia/Damascus'),
            'theme': user.get_preference('theme', 'light'),
            'push_enabled': user.get_preference('push_enabled', True),
            'email_notifications': user.get_preference('email_notifications', True)
        }
        
        return jsonify({'settings': settings}), 200
        
    except Exception as e:
        logger.error("user.settings_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


@users_bp.route('/settings', methods=['PUT'])
def update_settings():
    """Update user settings in database. / تحديث الإعدادات."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        allowed_keys = ['language', 'timezone', 'theme', 'push_enabled', 'email_notifications']
        
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        for key in allowed_keys:
            if key in data:
                user.set_preference(key, data[key])
        
        repo.update(user, {'preferences': user.preferences})
        
        logger.info("user.settings_updated", user_id=user_id)
        return jsonify({'message': 'Settings updated', 'message_ar': 'تم تحديث الإعدادات'}), 200
        
    except Exception as e:
        logger.error("user.settings_update_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 💳 Payment Methods - From user.preferences
# ============================================================

@users_bp.route('/payout-methods', methods=['GET'])
def payout_methods():
    """Get user payout methods from database. / طرق الدفع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        methods = user.get_preference('payout_methods', [
            {'method': 'usdt', 'address': '', 'verified': False}
        ])
        
        return jsonify({'methods': methods}), 200
        
    except Exception as e:
        logger.error("user.payout_methods_failed", error=str(e))
        return jsonify({'methods': []}), 200


@users_bp.route('/payout-methods', methods=['PUT'])
def update_payout_methods():
    """Update payout methods in database. / تحديث طرق الدفع."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        methods = data.get('methods', [])
        
        repo = _get_user_repo()
        user = repo.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found', 'message_ar': 'المستخدم غير موجود'}), 404
        
        user.set_preference('payout_methods', methods)
        repo.update(user, {'preferences': user.preferences})
        
        logger.info("user.payout_methods_updated", user_id=user_id)
        return jsonify({'message': 'Payment methods updated', 'message_ar': 'تم تحديث طرق الدفع'}), 200
        
    except Exception as e:
        logger.error("user.payout_methods_update_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


__all__ = ['users_bp']
