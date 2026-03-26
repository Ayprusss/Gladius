"""Unit tests for UnifiedMCPClient"""
import pytest
from unittest.mock import Mock, MagicMock
from src.mcp.unified_mcp_client import UnifiedMCPClient
from src.mcp.mock_mcp import MockMCPClient
from src.request_processor.request_adapter import DirectRequestAdapter


class TestUnifiedMCPClient:
    """Test UnifiedMCPClient functionality"""

    def test_ticket_id_delegates_to_ticket_mcp(self):
        """Test that ticket IDs are delegated to underlying MCP"""
        mock_mcp = Mock()
        mock_mcp.get_ticket.return_value = {
            "key": "PROJ-123",
            "title": "Test ticket",
            "description": "Test",
            "type": "feature"
        }

        unified_client = UnifiedMCPClient(mock_mcp)
        ticket = unified_client.get_ticket("PROJ-123")

        # Should have called underlying MCP
        mock_mcp.get_ticket.assert_called_once_with("PROJ-123")

        # Should have marked as ticket type
        assert ticket["_request_type"] == "ticket"
        assert ticket["_is_direct_request"] is False

    def test_natural_request_creates_synthetic(self):
        """Test that natural requests create synthetic tickets"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        ticket = unified_client.get_ticket("Add login button")

        # Should NOT have called underlying MCP
        mock_mcp.get_ticket.assert_not_called()

        # Should be synthetic ticket
        assert ticket["_is_direct_request"] is True
        assert ticket["_request_type"] == "natural"
        assert ticket["key"].startswith("DIRECT-")

    def test_failed_ticket_lookup_fallback(self, capsys):
        """Test fallback to synthetic when ticket not found"""
        mock_mcp = Mock()
        mock_mcp.get_ticket.side_effect = ValueError("Ticket not found")

        unified_client = UnifiedMCPClient(mock_mcp)
        ticket = unified_client.get_ticket("PROJ-999")

        # Should have tried underlying MCP
        mock_mcp.get_ticket.assert_called_once_with("PROJ-999")

        # Should fallback to synthetic
        assert ticket["_is_direct_request"] is True
        assert ticket["_request_type"] == "natural"

        # Should print warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "PROJ-999" in captured.out

    def test_synthetic_ticket_has_required_fields(self):
        """Test that synthetic tickets have all required fields"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        ticket = unified_client.get_ticket("Add feature")

        # Check standard fields
        assert "key" in ticket
        assert "title" in ticket
        assert "description" in ticket
        assert "type" in ticket
        assert "priority" in ticket
        assert "status" in ticket

    def test_ticket_marked_as_ticket_type(self):
        """Test that real tickets are marked correctly"""
        mock_mcp = MockMCPClient()
        unified_client = UnifiedMCPClient(mock_mcp)

        # PROJ-123 exists in MockMCPClient
        ticket = unified_client.get_ticket("PROJ-123")

        assert ticket["_request_type"] == "ticket"
        assert ticket["_is_direct_request"] is False

    def test_natural_marked_as_natural_type(self):
        """Test that natural requests are marked correctly"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        ticket = unified_client.get_ticket("Fix the bug")

        assert ticket["_request_type"] == "natural"
        assert ticket["_is_direct_request"] is True

    def test_health_check_delegates(self):
        """Test that health check delegates to underlying MCP"""
        mock_mcp = Mock()
        mock_mcp.health_check.return_value = True

        unified_client = UnifiedMCPClient(mock_mcp)
        result = unified_client.health_check()

        assert result is True
        mock_mcp.health_check.assert_called_once()

    def test_empty_request_handling(self):
        """Test handling of empty requests"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        with pytest.raises(ValueError, match="Invalid request"):
            unified_client.get_ticket("")

    def test_nonexistent_ticket_fallback(self, capsys):
        """Test fallback when ticket doesn't exist"""
        mock_mcp = Mock()
        mock_mcp.get_ticket.side_effect = KeyError("PROJ-999")

        unified_client = UnifiedMCPClient(mock_mcp)
        ticket = unified_client.get_ticket("PROJ-999")

        # Should create synthetic ticket
        assert ticket["_is_direct_request"] is True
        assert "Warning" in capsys.readouterr().out

    def test_connection_error_fallback(self, capsys):
        """Test fallback on connection errors"""
        mock_mcp = Mock()
        mock_mcp.get_ticket.side_effect = ConnectionError("Network error")

        unified_client = UnifiedMCPClient(mock_mcp)
        ticket = unified_client.get_ticket("PROJ-123")

        # Should fallback to synthetic
        assert ticket["_is_direct_request"] is True
        assert "Warning" in capsys.readouterr().out

    def test_synthetic_ticket_flags(self):
        """Test that synthetic tickets have correct flags"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        ticket = unified_client.get_ticket("Natural request")

        assert ticket["_is_direct_request"] is True
        assert ticket["_request_type"] == "natural"

    def test_adapter_integration(self):
        """Test integration with custom adapter"""
        mock_mcp = Mock()
        custom_adapter = DirectRequestAdapter(ticket_prefix="CUSTOM")

        unified_client = UnifiedMCPClient(mock_mcp, custom_adapter)
        ticket = unified_client.get_ticket("Add feature")

        # Should use custom adapter
        assert ticket["key"].startswith("CUSTOM-")

    def test_list_tickets_delegates(self):
        """Test that list_tickets delegates to underlying MCP"""
        mock_mcp = Mock()
        mock_mcp.list_tickets.return_value = [
            {"key": "PROJ-123", "title": "Test"}
        ]

        unified_client = UnifiedMCPClient(mock_mcp)
        tickets = unified_client.list_tickets()

        mock_mcp.list_tickets.assert_called_once()
        assert len(tickets) == 1

    def test_get_ticket_history_for_real_ticket(self):
        """Test getting history for real ticket"""
        mock_mcp = Mock()
        mock_mcp.get_ticket_history.return_value = [
            {"action": "created", "timestamp": "2024-01-01"}
        ]

        unified_client = UnifiedMCPClient(mock_mcp)
        history = unified_client.get_ticket_history("PROJ-123")

        mock_mcp.get_ticket_history.assert_called_once_with("PROJ-123")
        assert len(history) == 1

    def test_get_ticket_history_for_synthetic(self):
        """Test that synthetic tickets have no history"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        history = unified_client.get_ticket_history("DIRECT-20241217")

        # Should not call underlying MCP
        mock_mcp.get_ticket_history.assert_not_called()
        assert history == []

    def test_health_check_when_mcp_fails(self):
        """Test that health check returns True even if MCP is down"""
        mock_mcp = Mock()
        mock_mcp.health_check.side_effect = Exception("MCP down")

        unified_client = UnifiedMCPClient(mock_mcp)
        result = unified_client.health_check()

        # Should still return True (can handle direct requests)
        assert result is True

    def test_whitespace_handling(self):
        """Test handling of requests with whitespace"""
        mock_mcp = Mock()
        mock_mcp.get_ticket.return_value = {
            "key": "PROJ-123",
            "title": "Test"
        }

        unified_client = UnifiedMCPClient(mock_mcp)

        # Ticket with whitespace
        ticket = unified_client.get_ticket("  PROJ-123  ")
        mock_mcp.get_ticket.assert_called_with("PROJ-123")

    def test_multiline_request(self):
        """Test handling of multiline natural requests"""
        mock_mcp = Mock()
        unified_client = UnifiedMCPClient(mock_mcp)

        request = "Add feature\nwith multiple\nlines"
        ticket = unified_client.get_ticket(request)

        assert ticket["_is_direct_request"] is True
        assert "\n" in ticket["description"]
