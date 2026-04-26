"""
اختبارات دوال التحقق من صحة البيانات
Unit Tests for Data Validation Utilities
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from decimal import Decimal
import pytest

from src.app.models.validators import (
    validate_email,
    validate_username,
    validate_phone,
    validate_url,
    validate_amount,
    validate_uuid,
    validate_tron_address,
    validate_hex_color,
    validate_length,
    sanitize_string,
    sanitize_email,
    sanitize_username,
    sanitize_json,
    validate_required_fields,
    validate_all,
)


class TestValidateEmail:
    def test_valid_email(self):
        valid, result = validate_email("test@valid-domain.com")
        assert valid is True
    
    def test_valid_email_with_dots(self):
        valid, result = validate_email("user.name@valid-domain.co.uk")
        assert valid is True
    
    def test_invalid_email_no_at(self):
        valid, msg = validate_email("uservalid-domain.com")
        assert valid is False
    
    def test_invalid_email_no_domain(self):
        valid, msg = validate_email("user@")
        assert valid is False
    
    def test_empty_email(self):
        valid, msg = validate_email("")
        assert valid is False
    
    def test_blocked_domain(self):
        valid, msg = validate_email("user@example.com")
        assert valid is False
        assert "not allowed" in msg
    
    def test_too_long_email(self):
        long_email = "a" * 250 + "@valid-domain.com"
        valid, msg = validate_email(long_email)
        assert valid is False


class TestValidateUsername:
    def test_valid_username(self):
        valid, result = validate_username("john_doe123")
        assert valid is True
    
    def test_username_too_short(self):
        valid, msg = validate_username("ab")
        assert valid is False
    
    def test_username_too_long(self):
        valid, msg = validate_username("a" * 33)
        assert valid is False
    
    def test_username_starts_with_number(self):
        valid, msg = validate_username("1john")
        assert valid is False
    
    def test_username_special_chars(self):
        valid, msg = validate_username("john@doe")
        assert valid is False
    
    def test_reserved_username(self):
        valid, msg = validate_username("admin")
        assert valid is False


class TestValidatePhone:
    def test_valid_phone(self):
        valid, result = validate_phone("+966501234567")
        assert valid is True
    
    def test_valid_phone_without_plus(self):
        valid, result = validate_phone("0501234567")
        assert valid is True
    
    def test_phone_with_spaces(self):
        valid, result = validate_phone("+966 50 123 4567")
        assert valid is True
    
    def test_empty_phone(self):
        valid, msg = validate_phone("")
        assert valid is False


class TestValidateUrl:
    def test_valid_http_url(self):
        valid, result = validate_url("http://valid-domain.com")
        assert valid is True
    
    def test_valid_https_url(self):
        valid, result = validate_url("https://valid-domain.com/path")
        assert valid is True
    
    def test_invalid_url(self):
        valid, msg = validate_url("not-a-url")
        assert valid is False


class TestValidateAmount:
    def test_valid_amount(self):
        valid, msg, value = validate_amount("100.50")
        assert valid is True
    
    def test_amount_below_min(self):
        valid, msg, value = validate_amount(5, min_amount=Decimal(10))
        assert valid is False
    
    def test_amount_above_max(self):
        valid, msg, value = validate_amount(100, max_amount=Decimal(50))
        assert valid is False
    
    def test_invalid_amount_format(self):
        valid, msg, value = validate_amount("not-a-number")
        assert valid is False
    
    def test_too_many_decimal_places(self):
        valid, msg, value = validate_amount("100.999", decimal_places=2)
        assert valid is False


class TestValidateUUID:
    def test_valid_uuid(self):
        valid, result = validate_uuid("123e4567-e89b-12d3-a456-426614174000")
        assert valid is True
    
    def test_invalid_uuid(self):
        valid, msg = validate_uuid("not-a-uuid")
        assert valid is False
    
    def test_empty_uuid(self):
        valid, msg = validate_uuid("")
        assert valid is False


class TestValidateTronAddress:
    def test_valid_tron_address(self):
        valid, result = validate_tron_address("T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb")
        assert valid is True
    
    def test_invalid_tron_address(self):
        valid, msg = validate_tron_address("0x1234567890")
        assert valid is False
    
    def test_tron_address_wrong_length(self):
        valid, msg = validate_tron_address("T123")
        assert valid is False


class TestValidateHexColor:
    def test_valid_hex_with_hash(self):
        valid, result = validate_hex_color("#FF0000")
        assert valid is True
    
    def test_valid_hex_without_hash(self):
        valid, result = validate_hex_color("00FF00")
        assert valid is True
    
    def test_valid_short_hex(self):
        valid, result = validate_hex_color("#FFF")
        assert valid is True
    
    def test_invalid_hex(self):
        valid, msg = validate_hex_color("not-a-color")
        assert valid is False


class TestValidateLength:
    def test_valid_length(self):
        valid, result = validate_length("hello", min_length=3, max_length=10)
        assert valid is True
    
    def test_too_short(self):
        valid, msg = validate_length("hi", min_length=5)
        assert valid is False
    
    def test_too_long(self):
        valid, msg = validate_length("hello world", max_length=5)
        assert valid is False


class TestSanitize:
    def test_sanitize_string_html(self):
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
    
    def test_sanitize_string_extra_spaces(self):
        result = sanitize_string("  hello   world  ")
        assert result == "hello world"
    
    def test_sanitize_string_max_length(self):
        result = sanitize_string("hello world", max_length=5)
        assert result == "hello"
    
    def test_sanitize_email(self):
        result = sanitize_email("  TEST@Valid-Domain.COM  ")
        assert result == "test@valid-domain.com"
    
    def test_sanitize_username(self):
        result = sanitize_username("  John@Doe!  ")
        assert result == "JohnDoe"
    
    def test_sanitize_json_dict(self):
        data = {"name": "  John  ", "nested": {"value": "<script>"}}
        result = sanitize_json(data)
        assert result["name"] == "John"
    
    def test_sanitize_json_list(self):
        data = ["  hello  ", "<b>world</b>"]
        result = sanitize_json(data)
        assert result[0] == "hello"


class TestBulkValidation:
    def test_validate_required_fields_all_present(self):
        data = {"name": "John", "email": "test@valid-domain.com"}
        valid, missing = validate_required_fields(data, ["name", "email"])
        assert valid is True
    
    def test_validate_required_fields_missing(self):
        data = {"name": "John"}
        valid, missing = validate_required_fields(data, ["name", "email"])
        assert valid is False
        assert "email" in missing
    
    def test_validate_all_valid(self):
        data = {
            "email": "test@valid-domain.com",
            "username": "john_doe",
            "phone": "+966501234567"
        }
        rules = {"email": "email", "username": "username", "phone": "phone"}
        valid, errors = validate_all(data, rules)
        assert valid is True
    
    def test_validate_all_invalid(self):
        data = {
            "email": "invalid-email",
            "username": "a",
            "phone": "123"
        }
        rules = {"email": "email", "username": "username", "phone": "phone"}
        valid, errors = validate_all(data, rules)
        assert valid is False


class TestIntegration:
    def test_full_validation_flow(self):
        data = {
            "email": "  TEST@Valid-Domain.COM  ",
            "username": "  John_Doe123  ",
            "phone": "+966 50 123 4567",
            "amount": "100.50",
            "tron_address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
        }
        data["email"] = sanitize_email(data["email"])
        data["username"] = sanitize_username(data["username"])
        assert validate_email(data["email"])[0] is True
        assert validate_username(data["username"])[0] is True
        assert validate_phone(data["phone"])[0] is True
        assert validate_amount(data["amount"])[0] is True
        assert validate_tron_address(data["tron_address"])[0] is True
