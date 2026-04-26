"""
Marshmallow Schemas - SafeSend API
مخططات Marshmallow للتحقق والتسلسل

Validates incoming requests and serializes outgoing responses.
يتحقق من صحة الطلبات الواردة ويسلسل الاستجابات الصادرة.
"""

from marshmallow import Schema, fields, validate, ValidationError
from flask import jsonify, request
from typing import Any, Optional, List, Dict
from functools import wraps

# ============================================================
# 📊 Pagination Schema
# ============================================================

class PaginationSchema(Schema):
    """Pagination metadata / بيانات التصفح"""
    page = fields.Integer(dump_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(dump_default=20, validate=validate.Range(min=1, max=100))
    total = fields.Integer()
    pages = fields.Integer()
    has_next = fields.Boolean()
    has_prev = fields.Boolean()

# ============================================================
# 🏥 Health Schema
# ============================================================

class HealthSchema(Schema):
    """System health status / حالة صحة النظام"""
    status = fields.String(required=True)
    timestamp = fields.DateTime()
    components = fields.Dict(keys=fields.String(), values=fields.Dict())

# ============================================================
# ❌ Error Schema
# ============================================================

class ErrorSchema(Schema):
    """Error response / استجابة خطأ"""
    error = fields.String(required=True)
    message = fields.String()
    message_ar = fields.String()
    status_code = fields.Integer()
    details = fields.Dict()

# ============================================================
# 👤 User Schemas
# ============================================================

class UserSchema(Schema):
    """User serialization / تسلسل المستخدم"""
    id = fields.Integer(dump_only=True)
    uuid = fields.UUID(dump_only=True)
    email = fields.Email(required=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    avatar = fields.String(allow_none=True)
    is_active = fields.Boolean(dump_only=True)
    is_verified = fields.Boolean(dump_only=True)
    rating = fields.Float(dump_only=True)
    total_reviews = fields.Integer(dump_only=True)
    completed_deals = fields.Integer(dump_only=True)
    preferred_payout_method = fields.String(dump_only=True)
    last_seen_at = fields.DateTime(dump_only=True)
    is_online = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class UserProfileSchema(Schema):
    """Public user profile / الملف الشخصي العام"""
    id = fields.Integer(dump_only=True)
    username = fields.String()
    avatar = fields.String(allow_none=True)
    rating = fields.Float()
    total_reviews = fields.Integer()
    completed_deals = fields.Integer()
    is_online = fields.Boolean()
    last_seen_at = fields.DateTime()

class UserCreateSchema(Schema):
    """User registration validation / التحقق من تسجيل مستخدم"""
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email is required / البريد الإلكتروني مطلوب',
            'invalid': 'Invalid email format / صيغة بريد إلكتروني غير صالحة'
        }
    )
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=80),
        error_messages={
            'required': 'Username is required / اسم المستخدم مطلوب',
            'validator_failed': 'Username must be 3-80 characters / يجب أن يكون 3-80 حرفاً'
        }
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=8, max=128),
        error_messages={
            'required': 'Password is required / كلمة المرور مطلوبة',
            'validator_failed': 'Password must be 8-128 characters / يجب أن تكون 8-128 حرفاً'
        }
    )

class UserUpdateSchema(Schema):
    """User update validation / التحقق من تحديث مستخدم"""
    email = fields.Email(allow_none=True)
    username = fields.String(validate=validate.Length(min=3, max=80), allow_none=True)
    avatar = fields.String(allow_none=True)
    push_enabled = fields.Boolean(allow_none=True)

# ============================================================
# 📋 Deal Schemas
# ============================================================

class DealSchema(Schema):
    """Deal serialization / تسلسل الصفقة"""
    id = fields.Integer(dump_only=True)
    uuid = fields.UUID(dump_only=True)
    seller_id = fields.Integer(required=True)
    buyer_id = fields.Integer(dump_only=True)
    title = fields.String(required=True, validate=validate.Length(min=5, max=200))
    description = fields.String(required=True, validate=validate.Length(min=20))
    category = fields.String(validate=validate.Length(max=50))
    amount_usdt = fields.Decimal(required=True, places=2)
    fee_percent = fields.Decimal(places=2, dump_only=True)
    platform_fee = fields.Decimal(places=2, dump_only=True)
    seller_amount = fields.Decimal(places=2, dump_only=True)
    status = fields.String(dump_only=True)
    substatus = fields.String(allow_none=True, dump_only=True)
    status_history = fields.List(fields.Dict(), dump_only=True)
    buyer_wallet = fields.String(dump_only=True)
    escrow_tx_hash = fields.String(dump_only=True)
    payout_method = fields.String(dump_only=True)
    payout_status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    expires_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime(allow_none=True, dump_only=True)

class DealCreateSchema(Schema):
    """Deal creation validation / التحقق من إنشاء صفقة"""
    title = fields.String(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    description = fields.String(
        required=True,
        validate=validate.Length(min=20)
    )
    category = fields.String(validate=validate.Length(max=50))
    amount_usdt = fields.Decimal(required=True, places=2)
    fee_percent = fields.Decimal(places=2, dump_default=5.0)

class DealUpdateSchema(Schema):
    """Deal update validation / التحقق من تحديث صفقة"""
    title = fields.String(validate=validate.Length(min=5, max=200), allow_none=True)
    description = fields.String(validate=validate.Length(min=20), allow_none=True)
    category = fields.String(allow_none=True)

class DealTimelineSchema(Schema):
    """Deal timeline serialization / تسلسل الجدول الزمني"""
    events = fields.List(fields.Dict())
    deal_uuid = fields.UUID()

# ============================================================
# 💰 Payment Schemas
# ============================================================

class PaymentSchema(Schema):
    """Payment serialization / تسلسل الدفع"""
    id = fields.Integer(dump_only=True)
    transaction_uuid = fields.UUID(dump_only=True)
    deal_id = fields.Integer()
    tx_type = fields.String()
    tx_hash = fields.String()
    amount_usdt = fields.Decimal(places=2)
    status = fields.String()
    created_at = fields.DateTime(dump_only=True)

class PayoutSchema(Schema):
    """Payout serialization / تسلسل المدفوعات"""
    id = fields.Integer(dump_only=True)
    deal_uuid = fields.UUID()
    amount_usdt = fields.Decimal(places=2)
    to_address = fields.String()
    status = fields.String()
    confirmed_at = fields.DateTime(allow_none=True)

# ============================================================
# 📁 File Schemas
# ============================================================

class FileSchema(Schema):
    """File serialization / تسلسل الملف"""
    id = fields.Integer(dump_only=True)
    deal_id = fields.Integer()
    original_name = fields.String()
    file_size = fields.Integer()
    mime_type = fields.String()
    encrypted = fields.Boolean()
    virus_scanned = fields.Boolean()
    virus_scan_result = fields.String(allow_none=True)
    download_count = fields.Integer()
    created_at = fields.DateTime(dump_only=True)

class FileUploadSchema(Schema):
    """File upload validation / التحقق من رفع ملف"""
    deal_uuid = fields.UUID(required=True)
    file_name = fields.String(required=True)
    file_size = fields.Integer(required=True, validate=validate.Range(max=104857600))  # 100MB
    mime_type = fields.String(required=True)

# ============================================================
# ⚠️ Dispute Schemas
# ============================================================

class DisputeSchema(Schema):
    """Dispute serialization / تسلسل النزاع"""
    id = fields.Integer(dump_only=True)
    dispute_uuid = fields.UUID(dump_only=True)
    deal_id = fields.Integer()
    opened_by_id = fields.Integer()
    reason = fields.String()
    reason_category = fields.String()
    evidence = fields.List(fields.Dict())
    status = fields.String()
    resolution = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

class DisputeCreateSchema(Schema):
    """Dispute creation validation / التحقق من إنشاء نزاع"""
    deal_uuid = fields.UUID(required=True)
    reason = fields.String(
        required=True,
        validate=validate.Length(min=10)
    )
    reason_category = fields.String(
        required=True,
        validate=validate.OneOf(['quality', 'communication', 'delivery', 'payment'])
    )

class DisputeEvidenceSchema(Schema):
    """Evidence upload validation / التحقق من إضافة دليل"""
    description = fields.String(required=True)
    file_ids = fields.List(fields.Integer(), validate=validate.Length(min=1))

# ============================================================
# 💬 Message Schemas
# ============================================================

class MessageSchema(Schema):
    """Message serialization / تسلسل الرسالة"""
    id = fields.Integer(dump_only=True)
    conversation_id = fields.Integer()
    sender_id = fields.Integer()
    content = fields.String()
    message_type = fields.String()
    is_read = fields.Boolean()
    attachments = fields.List(fields.Dict(), allow_none=True)
    created_at = fields.DateTime(dump_only=True)

class MessageCreateSchema(Schema):
    """Message creation validation / التحقق من إرسال رسالة"""
    content = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )
    message_type = fields.String(dump_default='text', validate=validate.OneOf(['text', 'file', 'system']))
    reply_to_id = fields.Integer(allow_none=True)

class ConversationSchema(Schema):
    """Conversation serialization / تسلسل المحادثة"""
    id = fields.Integer(dump_only=True)
    deal_id = fields.Integer()
    seller_id = fields.Integer()
    buyer_id = fields.Integer()
    last_message_at = fields.DateTime(allow_none=True)
    last_message_preview = fields.String(allow_none=True)
    is_active = fields.Boolean()

# ============================================================
# 📊 Transaction Schema
# ============================================================

class TransactionSchema(Schema):
    """Transaction serialization / تسلسل المعاملة"""
    id = fields.Integer(dump_only=True)
    transaction_uuid = fields.UUID(dump_only=True)
    deal_id = fields.Integer()
    user_id = fields.Integer()
    tx_type = fields.String()
    tx_hash = fields.String(allow_none=True)
    amount_usdt = fields.Decimal(places=2)
    status = fields.String()
    confirmed_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

# ============================================================
# 📜 Audit Log Schema
# ============================================================

class AuditLogSchema(Schema):
    """Audit log serialization / تسلسل سجل التدقيق"""
    id = fields.Integer(dump_only=True)
    trace_id = fields.String()
    user_id = fields.Integer()
    action = fields.String()
    entity_type = fields.String()
    entity_id = fields.Integer()
    ip_address = fields.String()
    created_at = fields.DateTime(dump_only=True)

# ============================================================
# 📊 Admin Stats Schema
# ============================================================

class AdminStatsSchema(Schema):
    """Admin statistics serialization / تسلسل إحصائيات المدير"""
    total_users = fields.Integer()
    active_deals = fields.Integer()
    completed_deals = fields.Integer()
    disputes_opened = fields.Integer()
    total_volume_usdt = fields.Decimal(places=2)
    platform_revenue = fields.Decimal(places=2)
    new_users_today = fields.Integer()
    new_deals_today = fields.Integer()

# ============================================================
# 🛠️ Validation & Serialization Helpers
# ============================================================

def validate_request(schema: Schema) -> callable:
    """
    Decorator to validate incoming request data against a schema.
    ديكورتر للتحقق من صحة بيانات الطلب مقابل المخطط.

    Returns:
        400 with validation errors if invalid.
    """
    def decorator(f: callable) -> callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            data = request.get_json(silent=True) or {}
            try:
                validated = schema.load(data)
            except ValidationError as err:
                return handle_validation_error(err)
            return f(validated_data=validated, *args, **kwargs)
        return wrapper
    return decorator

def serialize_response(schema: Schema, many: bool = False) -> callable:
    """
    Decorator to serialize function return value using a schema.
    ديكورتر لتسلسل القيمة المرجعة من الدالة.

    Returns:
        JSON response with serialized data.
    """
    def decorator(f: callable) -> callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                data, status_code = result
            else:
                data, status_code = result, 200
            
            serialized = schema.dump(data, many=many)
            return jsonify(serialized), status_code
        return wrapper
    return decorator

def handle_validation_error(error: ValidationError) -> tuple:
    """
    Handle marshmallow ValidationError and return 400 response.
    معالجة أخطاء التحقق وإرجاع استجابة 400.

    Returns:
        JSON response with 400 status.
    """
    error_messages = {
        'error': 'Validation failed',
        'message': 'Invalid request data',
        'message_ar': 'بيانات الطلب غير صالحة',
        'details': error.messages
    }
    return jsonify(error_messages), 400

# ============================================================
# 📦 Export
# ============================================================

__all__ = [
    'PaginationSchema',
    'HealthSchema',
    'ErrorSchema',
    'UserSchema',
    'UserProfileSchema',
    'UserCreateSchema',
    'UserUpdateSchema',
    'DealSchema',
    'DealCreateSchema',
    'DealUpdateSchema',
    'DealTimelineSchema',
    'PaymentSchema',
    'PayoutSchema',
    'FileSchema',
    'FileUploadSchema',
    'DisputeSchema',
    'DisputeCreateSchema',
    'DisputeEvidenceSchema',
    'MessageSchema',
    'MessageCreateSchema',
    'ConversationSchema',
    'TransactionSchema',
    'AuditLogSchema',
    'AdminStatsSchema',
    'validate_request',
    'serialize_response',
    'handle_validation_error'
]
