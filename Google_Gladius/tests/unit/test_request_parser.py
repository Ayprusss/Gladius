"""Unit tests for RequestParser"""
import pytest
from src.request_processor.request_parser import RequestParser, RequestType


class TestRequestParser:
    """Test RequestParser functionality"""

    def test_parse_valid_ticket_id(self):
        """Test parsing valid ticket IDs"""
        request_type, cleaned = RequestParser.parse("PROJ-123")
        assert request_type == RequestType.TICKET
        assert cleaned == "PROJ-123"

    def test_parse_natural_request(self):
        """Test parsing natural language requests"""
        request_type, cleaned = RequestParser.parse("Add login button")
        assert request_type == RequestType.NATURAL
        assert cleaned == "Add login button"

    def test_parse_ticket_with_whitespace(self):
        """Test parsing ticket ID with surrounding whitespace"""
        request_type, cleaned = RequestParser.parse("  TASK-456  ")
        assert request_type == RequestType.TICKET
        assert cleaned == "TASK-456"

    def test_parse_empty_string_raises(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            RequestParser.parse("")

    def test_parse_whitespace_only_raises(self):
        """Test that whitespace-only string raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            RequestParser.parse("   ")

    def test_parse_complex_ticket_format(self):
        """Test various ticket ID formats"""
        # Valid formats
        assert RequestParser.parse("ABC-1")[0] == RequestType.TICKET
        assert RequestParser.parse("PROJECT-999")[0] == RequestType.TICKET
        assert RequestParser.parse("X-1")[0] == RequestType.TICKET

    def test_parse_lowercase_ticket_rejected(self):
        """Test that lowercase ticket IDs are treated as natural"""
        request_type, _ = RequestParser.parse("proj-123")
        assert request_type == RequestType.NATURAL

    def test_parse_ticket_without_dash(self):
        """Test that ticket format without dash is natural"""
        request_type, _ = RequestParser.parse("PROJ123")
        assert request_type == RequestType.NATURAL

    def test_parse_multiline_request(self):
        """Test parsing multiline natural request"""
        multiline = "Add feature\nwith multiple lines"
        request_type, cleaned = RequestParser.parse(multiline)
        assert request_type == RequestType.NATURAL
        assert "\n" in cleaned

    def test_parse_long_request(self):
        """Test parsing very long natural request"""
        long_request = "A" * 500
        request_type, cleaned = RequestParser.parse(long_request)
        assert request_type == RequestType.NATURAL
        assert len(cleaned) == 500

    def test_parse_request_with_special_chars(self):
        """Test parsing request with special characters"""
        request = "Fix bug in @user's $variable"
        request_type, cleaned = RequestParser.parse(request)
        assert request_type == RequestType.NATURAL
        assert cleaned == request

    def test_parse_request_looks_like_ticket(self):
        """Test request that looks similar to ticket but isn't"""
        # Has lowercase
        assert RequestParser.parse("Proj-123")[0] == RequestType.NATURAL
        # Has extra dash
        assert RequestParser.parse("PROJ-123-456")[0] == RequestType.NATURAL
        # Has letters after dash
        assert RequestParser.parse("PROJ-ABC")[0] == RequestType.NATURAL

    def test_parse_multiple_sentences(self):
        """Test parsing request with multiple sentences"""
        request = "Add login. Make it secure. Add tests."
        request_type, cleaned = RequestParser.parse(request)
        assert request_type == RequestType.NATURAL
        assert cleaned == request

    def test_parse_unicode_characters(self):
        """Test parsing request with unicode characters"""
        request = "Add emoji support 😀"
        request_type, cleaned = RequestParser.parse(request)
        assert request_type == RequestType.NATURAL
        assert "😀" in cleaned

    def test_parse_numeric_only(self):
        """Test parsing numeric-only input"""
        request_type, _ = RequestParser.parse("12345")
        assert request_type == RequestType.NATURAL

    def test_parse_alphanumeric_only(self):
        """Test parsing alphanumeric without dash"""
        request_type, _ = RequestParser.parse("ABC123")
        assert request_type == RequestType.NATURAL

    def test_is_ticket_id_helper(self):
        """Test is_ticket_id helper method"""
        assert RequestParser.is_ticket_id("PROJ-123") is True
        assert RequestParser.is_ticket_id("Add feature") is False
        assert RequestParser.is_ticket_id("proj-123") is False
        assert RequestParser.is_ticket_id("  TASK-1  ") is True

    def test_parse_ticket_with_leading_zeros(self):
        """Test ticket ID with leading zeros"""
        request_type, cleaned = RequestParser.parse("PROJ-001")
        assert request_type == RequestType.TICKET
        assert cleaned == "PROJ-001"

    def test_parse_single_letter_prefix(self):
        """Test ticket with single letter prefix"""
        request_type, cleaned = RequestParser.parse("A-1")
        assert request_type == RequestType.TICKET
        assert cleaned == "A-1"

    def test_parse_request_with_dashes(self):
        """Test natural request containing dashes"""
        request = "Add user-friendly feature"
        request_type, cleaned = RequestParser.parse(request)
        assert request_type == RequestType.NATURAL
        assert cleaned == request
