"""Unit tests for DirectRequestAdapter"""
import pytest
from src.request_processor.request_adapter import DirectRequestAdapter


class TestDirectRequestAdapter:
    """Test DirectRequestAdapter functionality"""

    def test_create_synthetic_ticket_basic(self):
        """Test basic synthetic ticket creation"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Add login button")

        assert "key" in ticket
        assert ticket["title"] == "Add login button"
        assert ticket["description"] == "Add login button"
        assert ticket["type"] in ["bug", "feature", "improvement"]
        assert ticket["_is_direct_request"] is True
        assert ticket["_request_type"] == "natural"

    def test_synthetic_ticket_structure(self):
        """Test that synthetic ticket has all required fields"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Test request")

        # Check all required fields exist
        assert "key" in ticket
        assert "title" in ticket
        assert "description" in ticket
        assert "type" in ticket
        assert "priority" in ticket
        assert "status" in ticket
        assert "acceptance_criteria" in ticket
        assert "comments" in ticket
        assert "related_tickets" in ticket
        assert "_is_direct_request" in ticket
        assert "_request_type" in ticket

    def test_title_extraction_short_request(self):
        """Test title extraction from short request"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Short request")

        assert ticket["title"] == "Short request"

    def test_title_extraction_long_request(self):
        """Test title extraction from very long request"""
        adapter = DirectRequestAdapter()
        long_request = "A" * 150
        ticket = adapter.create_synthetic_ticket(long_request)

        assert len(ticket["title"]) <= 103  # 100 + "..."
        assert ticket["title"].endswith("...")
        assert ticket["description"] == long_request

    def test_title_extraction_multiline(self):
        """Test title extraction from multiline request"""
        adapter = DirectRequestAdapter()
        multiline = "First line.\nSecond line.\nThird line."
        ticket = adapter.create_synthetic_ticket(multiline)

        assert ticket["title"] == "First line"
        assert ticket["description"] == multiline

    def test_type_detection_integration(self):
        """Test that type detection integrates correctly"""
        adapter = DirectRequestAdapter()

        bug_ticket = adapter.create_synthetic_ticket("Fix the login bug")
        assert bug_ticket["type"] == "bug"

        feature_ticket = adapter.create_synthetic_ticket("Add new feature")
        assert feature_ticket["type"] == "feature"

        improvement_ticket = adapter.create_synthetic_ticket("Refactor code")
        assert improvement_ticket["type"] == "improvement"

    def test_synthetic_ticket_id_format(self):
        """Test that ticket ID has correct format"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Test")

        assert ticket["key"].startswith("DIRECT-")
        # Should have timestamp: DIRECT-YYYYMMDDHHMMSS
        assert len(ticket["key"]) >= 21  # DIRECT- + 14 digit timestamp (and optional suffix)

    def test_synthetic_ticket_id_uniqueness(self):
        """Test that consecutive tickets get unique IDs"""
        adapter = DirectRequestAdapter()

        tickets = adapter.create_tickets_batch([
            "Request 1",
            "Request 2",
            "Request 3"
        ])

        ids = [t["key"] for t in tickets]
        assert len(ids) == len(set(ids))  # All unique

    def test_priority_override(self):
        """Test overriding default priority"""
        adapter = DirectRequestAdapter()

        # Default priority
        ticket1 = adapter.create_synthetic_ticket("Test")
        assert ticket1["priority"] == "medium"

        # Custom priority
        ticket2 = adapter.create_synthetic_ticket("Test", priority="high")
        assert ticket2["priority"] == "high"

    def test_type_override(self):
        """Test overriding auto-detected type"""
        adapter = DirectRequestAdapter()

        # Auto-detect (would be feature)
        ticket1 = adapter.create_synthetic_ticket("Add something")
        assert ticket1["type"] == "feature"

        # Override to bug
        ticket2 = adapter.create_synthetic_ticket("Add something", ticket_type="bug")
        assert ticket2["type"] == "bug"

    def test_empty_request_raises(self):
        """Test that empty request raises ValueError"""
        adapter = DirectRequestAdapter()

        with pytest.raises(ValueError, match="cannot be empty"):
            adapter.create_synthetic_ticket("")

    def test_whitespace_only_request_raises(self):
        """Test that whitespace-only request raises ValueError"""
        adapter = DirectRequestAdapter()

        with pytest.raises(ValueError, match="cannot be empty"):
            adapter.create_synthetic_ticket("   ")

    def test_custom_ticket_prefix(self):
        """Test using custom ticket prefix"""
        adapter = DirectRequestAdapter(ticket_prefix="CUSTOM")
        ticket = adapter.create_synthetic_ticket("Test")

        assert ticket["key"].startswith("CUSTOM-")

    def test_create_tickets_batch(self):
        """Test batch ticket creation"""
        adapter = DirectRequestAdapter()
        requests = ["Request 1", "Request 2", "Request 3"]

        tickets = adapter.create_tickets_batch(requests)

        assert len(tickets) == 3
        assert all(t["_is_direct_request"] for t in tickets)
        assert all(t["key"].startswith("DIRECT-") for t in tickets)

    def test_title_extraction_sentence_boundary(self):
        """Test title extraction stops at sentence boundary"""
        adapter = DirectRequestAdapter()
        request = "Add login. Make it secure. Add tests."
        ticket = adapter.create_synthetic_ticket(request)

        assert ticket["title"] == "Add login"

    def test_title_extraction_word_boundary(self):
        """Test title truncation at word boundary"""
        adapter = DirectRequestAdapter()
        # Create request just over 100 chars
        request = "Add " + "feature " * 20  # "feature " is 8 chars
        ticket = adapter.create_synthetic_ticket(request)

        # Title should be truncated at word boundary
        assert len(ticket["title"]) <= 103
        assert ticket["title"].endswith("...")
        assert not ticket["title"].endswith("tur...")  # Not mid-word

    def test_synthetic_ticket_status(self):
        """Test that synthetic tickets have 'open' status"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Test")

        assert ticket["status"] == "open"

    def test_synthetic_ticket_empty_lists(self):
        """Test that lists are initialized as empty"""
        adapter = DirectRequestAdapter()
        ticket = adapter.create_synthetic_ticket("Test")

        assert ticket["acceptance_criteria"] == []
        assert ticket["comments"] == []
        assert ticket["related_tickets"] == []

    def test_request_with_special_characters(self):
        """Test request with special characters"""
        adapter = DirectRequestAdapter()
        request = "Fix bug in @user's $variable"
        ticket = adapter.create_synthetic_ticket(request)

        assert ticket["description"] == request
        assert "@" in ticket["title"]
        assert "$" in ticket["title"]

    def test_batch_with_custom_settings(self):
        """Test batch creation with custom type and priority"""
        adapter = DirectRequestAdapter()
        tickets = adapter.create_tickets_batch(
            ["Request 1", "Request 2"],
            ticket_type="bug",
            priority="high"
        )

        assert all(t["type"] == "bug" for t in tickets)
        assert all(t["priority"] == "high" for t in tickets)
