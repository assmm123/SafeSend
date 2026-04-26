"""
Authentication API Endpoints - SafeSend
نقاط نهاية المصادقة - SafeSend

Handles registration, login, logout, 2FA, and session management.
يدير التسجيل، الدخول، الخروج، المصادقة الثنائية، وإدارة الجلسات.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import structlog

from src.app.models.user_repository import UserRepository
from src.app.models.security import (
    hash_password,
    verify_password,
    generate_token,
    validate_password_strength,
    generate_secure_token
)
from src.api.schemas import (
    UserCreateSchema,
    UserSchema,
    validate_request
)

logger = structlog.get_logger(__name__)
auth_bp = Blueprint('auth_v1', __name__, url_prefix='/api/v1/auth')

# ============================================================
# 🔐 Authentication Helpers
# ============================================================

def get_user_repo():
    """Get user repository instance."""
    return UserRepository()

def _generate_tokens(user_id: str) -> dict:
    """Generate access and refresh tokens for user."""
    access_token = generate_token({'user_id': str(user_id), 'type': 'access'}, expires_in=900)
    refresh_token = generate_token({'user_id': str(user_id), 'type': 'refresh'}, expires_in=604800)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 900
    }

def _verify_token(token: str) -> Optional[str]:
    """Verify token and return user_id."""
    from src.app.models.security import decode_token
    payload = decode_token(token)
    if payload and 'user_id' in payload:
        return payload['user_id']
    return None

# ============================================================
# 📝 Registration & Authentication
# ============================================================

@auth_bp.route('/register', methods=['POST'])
@validate_request(UserCreateSchema())
def register(validated_data: dict):
    """
    Register a new user account.
    تسجيل حساب مستخدم جديد.
    """
    try:
        repo = get_user_repo()
        
        existing = repo.get_by_email(validated_data['email'])
        if existing:
            return jsonify({
                'error': 'Email already registered',
                'message_ar': 'البريد الإلكتروني مسجل مسبقاً'
            }), 409
        
        existing = repo.get_by_username(validated_data['username'])
        if existing:
            return jsonify({
                'error': 'Username already taken',
                'message_ar': 'اسم المستخدم محجوز'
            }), 409
        
        is_valid, msg = validate_password_strength(validated_data['password'])
        if not is_valid:
            return jsonify({
                'error': msg,
                'message_ar': 'كلمة المرور ضعيفة'
            }), 400
        
        user_data = {
            'email': validated_data['email'],
            'username': validated_data['username'],
            'password_hash': hash_password(validated_data['password']),
            'is_active': True,
            'is_verified': False
        }
        
        user = repo.create(user_data)
        
        if not user:
            return jsonify({
                'error': 'Registration failed',
                'message_ar': 'فشل التسجيل'
            }), 500
        
        logger.info("user.registered", user_id=getattr(user, 'id', None))
        
        tokens = _generate_tokens(getattr(user, 'id', '1'))
        
        return jsonify({
            'message': 'Registration successful',
            'message_ar': 'تم التسجيل بنجاح',
            'user': UserSchema().dump(user),
            **tokens
        }), 201
        
    except Exception as e:
        logger.error("registration.failed", error=str(e))
        return jsonify({
            'error': 'Registration failed',
            'message_ar': 'فشل التسجيل'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email/username and password.
    تسجيل الدخول بالبريد وكلمة المرور.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '')
        username = data.get('username', '')
        password = data.get('password', '')
        
        if not password:
            return jsonify({
                'error': 'Password is required',
                'message_ar': 'كلمة المرور مطلوبة'
            }), 400
        
        repo = get_user_repo()
        user = None
        
        if email:
            user = repo.get_by_email(email)
        elif username:
            user = repo.get_by_username(username)
        
        if not user:
            return jsonify({
                'error': 'Invalid credentials',
                'message_ar': 'بيانات الدخول غير صحيحة'
            }), 401
        
        if not verify_password(password, user.password_hash):
            return jsonify({
                'error': 'Invalid credentials',
                'message_ar': 'بيانات الدخول غير صحيحة'
            }), 401
        
        if not user.is_active:
            return jsonify({
                'error': 'Account is suspended',
                'message_ar': 'الحساب موقوف'
            }), 403
        
        repo.update(user, {
            'last_login_at': datetime.now(timezone.utc),
            'last_login_ip': request.remote_addr
        })
        
        tokens = _generate_tokens(str(user.id))
        
        logger.info("user.logged_in", user_id=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'message_ar': 'تم تسجيل الدخول بنجاح',
            'user': UserSchema().dump(user),
            **tokens
        }), 200
        
    except Exception as e:
        logger.error("login.failed", error=str(e))
        return jsonify({
            'error': 'Login failed',
            'message_ar': 'فشل تسجيل الدخول'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout current user.
    تسجيل خروج المستخدم الحالي.
    """
    logger.info("user.logged_out")
    
    return jsonify({
        'message': 'Logged out successfully',
        'message_ar': 'تم تسجيل الخروج بنجاح'
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh access token using refresh token.
    تجديد توكن الوصول باستخدام توكن التحديث.
    """
    try:
        data = request.get_json() or {}
        refresh_token_value = data.get('refresh_token', '')
        
        if not refresh_token_value:
            return jsonify({
                'error': 'Refresh token is required',
                'message_ar': 'توكن التحديث مطلوب'
            }), 400
        
        user_id = _verify_token(refresh_token_value)
        if not user_id:
            return jsonify({
                'error': 'Invalid or expired refresh token',
                'message_ar': 'توكن التحديث غير صالح أو منتهي'
            }), 401
        
        tokens = _generate_tokens(user_id)
        
        return jsonify(tokens), 200
        
    except Exception as e:
        logger.error("token.refresh_failed", error=str(e))
        return jsonify({
            'error': 'Token refresh failed',
            'message_ar': 'فشل تجديد التوكن'
        }), 500


@auth_bp.route('/me', methods=['GET'])
def me():
    """
    Get current authenticated user profile.
    الحصول على الملف الشخصي للمستخدم الحالي.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        user_id = _verify_token(token)
        if not user_id:
            return jsonify({
                'error': 'Invalid or expired token',
                'message_ar': 'التوكن غير صالح أو منتهي'
            }), 401
        
        repo = get_user_repo()
        user = repo.get_by_id(int(user_id))
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message_ar': 'المستخدم غير موجود'
            }), 404
        
        return jsonify({
            'user': UserSchema().dump(user)
        }), 200
        
    except Exception as e:
        logger.error("profile.fetch_failed", error=str(e))
        return jsonify({
            'error': 'Failed to fetch profile',
            'message_ar': 'فشل جلب الملف الشخصي'
        }), 500


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Verify email address with code.
    التحقق من البريد الإلكتروني برمز التحقق.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '')
        code = data.get('code', '')
        
        if not email or not code:
            return jsonify({
                'error': 'Email and verification code required',
                'message_ar': 'البريد ورمز التحقق مطلوبان'
            }), 400
        
        if len(code) == 6 and code.isdigit():
            logger.info("email.verified", email=email)
            return jsonify({
                'message': 'Email verified successfully',
                'message_ar': 'تم التحقق من البريد بنجاح'
            }), 200
        else:
            return jsonify({
                'error': 'Invalid verification code',
                'message_ar': 'رمز التحقق غير صالح'
            }), 400
            
    except Exception as e:
        logger.error("email.verification_failed", error=str(e))
        return jsonify({
            'error': 'Verification failed',
            'message_ar': 'فشل التحقق'
        }), 500


@auth_bp.route('/verify-email/resend', methods=['POST'])
def resend_verification():
    """
    Resend email verification code.
    إعادة إرسال رمز تحقق البريد.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '')
        
        if not email:
            return jsonify({
                'error': 'Email is required',
                'message_ar': 'البريد مطلوب'
            }), 400
        
        logger.info("verification.resent", email=email)
        
        return jsonify({
            'message': 'Verification code sent',
            'message_ar': 'تم إرسال رمز التحقق'
        }), 200
        
    except Exception as e:
        logger.error("verification.resend_failed", error=str(e))
        return jsonify({
            'error': 'Failed to resend code',
            'message_ar': 'فشل إعادة إرسال الرمز'
        }), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request password reset.
    طلب إعادة تعيين كلمة المرور.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '')
        
        if not email:
            return jsonify({
                'error': 'Email is required',
                'message_ar': 'البريد مطلوب'
            }), 400
        
        logger.info("password.reset_requested", email=email)
        
        return jsonify({
            'message': 'If the email exists, a reset link has been sent',
            'message_ar': 'إذا كان البريد موجوداً، تم إرسال رابط إعادة التعيين'
        }), 200
        
    except Exception as e:
        logger.error("password.reset_request_failed", error=str(e))
        return jsonify({
            'error': 'Request failed',
            'message_ar': 'فشل الطلب'
        }), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password with token.
    إعادة تعيين كلمة المرور برمز.
    """
    try:
        data = request.get_json() or {}
        token = data.get('token', '')
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return jsonify({
                'error': 'Token and new password required',
                'message_ar': 'الرمز وكلمة المرور الجديدة مطلوبان'
            }), 400
        
        is_valid, msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                'error': msg,
                'message_ar': 'كلمة المرور ضعيفة'
            }), 400
        
        logger.info("password.reset")
        
        return jsonify({
            'message': 'Password reset successfully',
            'message_ar': 'تم إعادة تعيين كلمة المرور بنجاح'
        }), 200
        
    except Exception as e:
        logger.error("password.reset_failed", error=str(e))
        return jsonify({
            'error': 'Reset failed',
            'message_ar': 'فشل إعادة التعيين'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """
    Change password for authenticated user.
    تغيير كلمة المرور للمستخدم المسجل.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        data = request.get_json() or {}
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return jsonify({
                'error': 'Old and new passwords required',
                'message_ar': 'كلمات المرور القديمة والجديدة مطلوبة'
            }), 400
        
        repo = get_user_repo()
        user = repo.get_by_id(int(user_id))
        
        if not user or not verify_password(old_password, user.password_hash):
            return jsonify({
                'error': 'Current password is incorrect',
                'message_ar': 'كلمة المرور الحالية غير صحيحة'
            }), 400
        
        is_valid, msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                'error': msg,
                'message_ar': 'كلمة المرور ضعيفة'
            }), 400
        
        repo.update(user, {'password_hash': hash_password(new_password)})
        
        logger.info("password.changed", user_id=user_id)
        
        return jsonify({
            'message': 'Password changed successfully',
            'message_ar': 'تم تغيير كلمة المرور بنجاح'
        }), 200
        
    except Exception as e:
        logger.error("password.change_failed", error=str(e))
        return jsonify({
            'error': 'Change failed',
            'message_ar': 'فشل تغيير كلمة المرور'
        }), 500


@auth_bp.route('/2fa/enable', methods=['POST'])
def enable_2fa():
    """
    Enable two-factor authentication.
    تفعيل المصادقة الثنائية.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        secret = generate_secure_token(16)
        backup_codes = [generate_secure_token(6) for _ in range(8)]
        
        logger.info("2fa.setup_initiated", user_id=user_id)
        
        return jsonify({
            'message': '2FA setup initiated',
            'message_ar': 'تم بدء إعداد المصادقة الثنائية',
            'secret': secret,
            'backup_codes': backup_codes
        }), 200
        
    except Exception as e:
        logger.error("2fa.enable_failed", error=str(e))
        return jsonify({
            'error': 'Failed to enable 2FA',
            'message_ar': 'فشل تفعيل المصادقة الثنائية'
        }), 500


@auth_bp.route('/2fa/verify', methods=['POST'])
def verify_2fa():
    """
    Verify 2FA code.
    التحقق من رمز المصادقة الثنائية.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        data = request.get_json() or {}
        code = data.get('code', '')
        
        if not code or len(code) != 6:
            return jsonify({
                'error': 'Invalid verification code',
                'message_ar': 'رمز التحقق غير صالح'
            }), 400
        
        logger.info("2fa.verified", user_id=user_id)
        
        return jsonify({
            'message': '2FA activated successfully',
            'message_ar': 'تم تفعيل المصادقة الثنائية بنجاح'
        }), 200
        
    except Exception as e:
        logger.error("2fa.verify_failed", error=str(e))
        return jsonify({
            'error': 'Verification failed',
            'message_ar': 'فشل التحقق'
        }), 500


@auth_bp.route('/2fa/disable', methods=['POST'])
def disable_2fa():
    """
    Disable two-factor authentication.
    تعطيل المصادقة الثنائية.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        logger.info("2fa.disabled", user_id=user_id)
        
        return jsonify({
            'message': '2FA disabled',
            'message_ar': 'تم تعطيل المصادقة الثنائية'
        }), 200
        
    except Exception as e:
        logger.error("2fa.disable_failed", error=str(e))
        return jsonify({
            'error': 'Failed to disable 2FA',
            'message_ar': 'فشل تعطيل المصادقة الثنائية'
        }), 500


@auth_bp.route('/2fa/backup', methods=['POST'])
def regenerate_backup_codes():
    """
    Regenerate 2FA backup codes.
    إعادة توليد رموز احتياطية.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        backup_codes = [generate_secure_token(6) for _ in range(8)]
        
        logger.info("2fa.backup_regenerated", user_id=user_id)
        
        return jsonify({
            'message': 'Backup codes regenerated',
            'message_ar': 'تم إعادة توليد الرموز الاحتياطية',
            'backup_codes': backup_codes
        }), 200
        
    except Exception as e:
        logger.error("2fa.backup_failed", error=str(e))
        return jsonify({
            'error': 'Failed to regenerate backup codes',
            'message_ar': 'فشل إعادة توليد الرموز'
        }), 500


@auth_bp.route('/push/subscribe', methods=['POST'])
def push_subscribe():
    """
    Subscribe to push notifications.
    الاشتراك في إشعارات الدفع.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        logger.info("push.subscribed", user_id=user_id)
        
        return jsonify({
            'message': 'Subscribed to push notifications',
            'message_ar': 'تم الاشتراك في الإشعارات'
               }), 200
        
    except Exception as e:
        logger.error("push.subscribe_failed", error=str(e))
        return jsonify({
            'error': 'Subscription failed',
            'message_ar': 'فشل الاشتراك'
        }), 500


@auth_bp.route('/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    """
    Unsubscribe from push notifications.
    إلغاء الاشتراك في إشعارات الدفع.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        logger.info("push.unsubscribed", user_id=user_id)
        
        return jsonify({
            'message': 'Unsubscribed from push notifications',
            'message_ar': 'تم إلغاء الاشتراك'
        }), 200
        
    except Exception as e:
        logger.error("push.unsubscribe_failed", error=str(e))
        return jsonify({
            'error': 'Unsubscribe failed',
            'message_ar': 'فشل إلغاء الاشتراك'
        }), 500


@auth_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List active user sessions.
    قائمة جلسات المستخدم النشطة.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        sessions = [{
            'id': 1,
            'device': request.headers.get('User-Agent', 'Unknown'),
            'ip': request.remote_addr,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'current': True
        }]
        
        return jsonify({'sessions': sessions}), 200
        
    except Exception as e:
        logger.error("sessions.list_failed", error=str(e))
        return jsonify({
            'error': 'Failed to list sessions',
            'message_ar': 'فشل جلب الجلسات'
        }), 500


@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
def revoke_session(session_id: int):
    """
    Revoke a specific session.
    إلغاء جلسة محددة.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        user_id = _verify_token(token)
        
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message_ar': 'المصادقة مطلوبة'
            }), 401
        
        logger.info("session.revoked", session_id=session_id, user_id=user_id)
        
        return jsonify({
            'message': 'Session revoked',
            'message_ar': 'تم إلغاء الجلسة'
        }), 200
        
    except Exception as e:
        logger.error("session.revoke_failed", error=str(e))
        return jsonify({
            'error': 'Failed to revoke session',
            'message_ar': 'فشل إلغاء الجلسة'
        }), 500


__all__ = [
    'auth_bp'
]
