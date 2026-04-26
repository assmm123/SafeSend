"""
اختبارات schemas.py
Unit Tests for schemas.py
"""

import pytest
from flask import Flask
from marshmallow import ValidationError

import sys
sys.path.insert(0, '.')

from src.api.schemas import (
    PaginationSchema,
    HealthSchema,
    ErrorSchema,
    UserSchema,
    UserProfileSchema,
    UserCreateSchema,
    UserUpdateSchema,
    DealSchema,
    DealCreateSchema,
    DealUpdateSchema,
    DealTimelineSchema,
    PaymentSchema,
    PayoutSchema,
    FileSchema,
    FileUploadSchema,
    DisputeSchema,
    DisputeCreateSchema,
    DisputeEvidenceSchema,
    MessageSchema,
    MessageCreateSchema,
    ConversationSchema,
    TransactionSchema,
    AuditLogSchema,
    AdminStatsSchema,
    handle_validation_error
)

@pytest.fixture
def app():
    """Create test Flask application for context."""
    app = Flask(__name__)
    return app

class TestUserCreateSchema:
    """Tests for user creation validation."""
    
    def test_valid_user_data(self):
        """Verify valid data passes validation."""
        data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'password123'
        }
        result = UserCreateSchema().load(data)
        assert result['email'] == 'test@example.com'
        assert result['username'] == 'testuser'
    
    def test_missing_email(self):
        """Verify missing email raises error."""
        data = {'username': 'testuser', 'password': 'password123'}
        with pytest.raises(ValidationError):
            UserCreateSchema().load(data)
    
    def test_invalid_email(self):
        """Verify invalid email raises error."""
        data = {'email': 'invalid', 'username': 'testuser', 'password': 'password123'}
        with pytest.raises(ValidationError):
            UserCreateSchema().load(data)
    
    def test_short_username(self):
        """Verify short username raises error."""
        data = {'email': 'test@example.com', 'username': 'ab', 'password': 'password123'}
        with pytest.raises(ValidationError):
            UserCreateSchema().load(data)
    
    def test_short_password(self):
        """Verify short password raises error."""
        data = {'email': 'test@example.com', 'username': 'testuser', 'password': '123'}
        with pytest.raises(ValidationError):
            UserCreateSchema().load(data)

class TestUserUpdateSchema:
    """Tests for user update validation."""
    
    def test_partial_update(self):
        """Verify partial update works."""
        data = {'username': 'newuser'}
        result = UserUpdateSchema().load(data)
        assert result['username'] == 'newuser'
    
    def test_empty_update(self):
        """Verify empty update works."""
        result = UserUpdateSchema().load({})
        assert result == {}

class TestDealCreateSchema:
    """Tests for deal creation validation."""
    
    def test_valid_deal(self):
        """Verify valid deal data passes."""
        data = {
            'title': 'Test Deal Title',
            'description': 'This is a test deal description long enough',
            'category': 'development',
            'amount_usdt': '100.00'
        }
        result = DealCreateSchema().load(data)
        assert result['title'] == 'Test Deal Title'
        assert result['amount_usdt'] == 100.00
    
    def test_short_title(self):
        """Verify short title raises error."""
        data = {
            'title': 'Hi',
            'description': 'This is a test deal description long enough',
            'amount_usdt': '100.00'
        }
        with pytest.raises(ValidationError):
            DealCreateSchema().load(data)
    
    def test_short_description(self):
        """Verify short description raises error."""
        data = {
            'title': 'Test Deal Title',
            'description': 'Short',
            'amount_usdt': '100.00'
        }
        with pytest.raises(ValidationError):
            DealCreateSchema().load(data)

class TestDisputeCreateSchema:
    """Tests for dispute creation validation."""
    
    def test_valid_dispute(self):
        """Verify valid dispute data passes."""
        data = {
            'deal_uuid': '12345678-1234-1234-1234-123456789abc',
            'reason': 'The work quality is not acceptable as described',
            'reason_category': 'quality'
        }
        result = DisputeCreateSchema().load(data)
        assert result['reason_category'] == 'quality'
    
    def test_invalid_category(self):
        """Verify invalid category raises error."""
        data = {
            'deal_uuid': '12345678-1234-1234-1234-123456789abc',
            'reason': 'The work quality is not acceptable as described',
            'reason_category': 'invalid'
        }
        with pytest.raises(ValidationError):
            DisputeCreateSchema().load(data)

class TestFileUploadSchema:
    """Tests for file upload validation."""
    
    def test_valid_upload(self):
        """Verify valid upload data passes."""
        data = {
            'deal_uuid': '12345678-1234-1234-1234-123456789abc',
            'file_name': 'test.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf'
        }
        result = FileUploadSchema().load(data)
        assert result['file_name'] == 'test.pdf'
    
    def test_file_too_large(self):
        """Verify file over 100MB raises error."""
        data = {
            'deal_uuid': '12345678-1234-1234-1234-123456789abc',
            'file_name': 'big.pdf',
            'file_size': 200000000,
            'mime_type': 'application/pdf'
        }
        with pytest.raises(ValidationError):
            FileUploadSchema().load(data)

class TestMessageCreateSchema:
    """Tests for message creation validation."""
    
    def test_valid_message(self):
        """Verify valid message passes."""
        data = {'content': 'Hello', 'message_type': 'text'}
        result = MessageCreateSchema().load(data)
        assert result['content'] == 'Hello'
    
    def test_empty_message(self):
        """Verify empty message raises error."""
        data = {'content': ''}
        with pytest.raises(ValidationError):
            MessageCreateSchema().load(data)

class TestPaginationSchema:
    """Tests for pagination schema."""
    
    def test_dump_default_values(self):
        """Verify default pagination values in dump."""
        schema = PaginationSchema()
        result = schema.dump({})
        assert result['page'] == 1
        assert result['per_page'] == 20

class TestAdminStatsSchema:
    """Tests for admin stats schema."""
    
    def test_serialization(self):
        """Verify admin stats serialization."""
        data = {
            'total_users': 100,
            'active_deals': 50,
            'completed_deals': 200,
            'disputes_opened': 5,
            'total_volume_usdt': '10000.00',
            'platform_revenue': '500.00',
            'new_users_today': 10,
            'new_deals_today': 5
        }
        result = AdminStatsSchema().dump(data)
        assert result['total_users'] == 100

class TestHandleValidationError:
    """Tests for validation error handler."""
    
    def test_returns_400(self, app):
        """Verify that handler returns 400 status."""
        error = ValidationError({'email': ['Not a valid email']})
        with app.app_context():
            response, status = handle_validation_error(error)
            assert status == 400

class TestHealthSchema:
    """Tests for health schema."""
    
    def test_valid_health(self):
        """Verify health data serialization."""
        data = {'status': 'healthy'}
        result = HealthSchema().dump(data)
        assert result['status'] == 'healthy'

class TestErrorSchema:
    """Tests for error schema."""
    
    def test_error_serialization(self):
        """Verify error data serialization."""
        data = {'error': 'Not found'}
        result = ErrorSchema().dump(data)
        assert result['error'] == 'Not found'

__all__ = [
    'TestUserCreateSchema',
    'TestUserUpdateSchema',
    'TestDealCreateSchema',
    'TestDisputeCreateSchema',
    'TestFileUploadSchema',
    'TestMessageCreateSchema',
    'TestPaginationSchema',
    'TestAdminStatsSchema',
    'TestHandleValidationError',
    'TestHealthSchema',
    'TestErrorSchema'
]
