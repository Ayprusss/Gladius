"""Unified MCP client supporting both ticket IDs and direct requests"""
from typing import Dict, Any, Optional
from .mcp_client import MCPClient
from ..request_processor.request_parser import RequestParser, RequestType
from ..request_processor.request_adapter import DirectRequestAdapter


class UnifiedMCPClient(MCPClient):
    """MCP client supporting both ticket IDs and direct requests"""

    def __init__(
        self,
        ticket_mcp_client: MCPClient,
        request_adapter: Optional[DirectRequestAdapter] = None
    ):
        """
        Initialize unified MCP client

        This client acts as a facade, routing requests to either:
        1. The underlying ticket MCP (for PROJ-123 style ticket IDs)
        2. The request adapter (for natural language requests)

        Args:
            ticket_mcp_client: MCP client for fetching actual tickets
            request_adapter: Adapter for creating synthetic tickets
                           (default: creates new DirectRequestAdapter)
        """
        self.ticket_mcp = ticket_mcp_client
        self.adapter = request_adapter or DirectRequestAdapter()
        self.parser = RequestParser()

    def get_ticket(self, request: str) -> Dict[str, Any]:
        """
        Handle both ticket IDs and natural requests

        Processing logic:
        1. Parse input to determine type (TICKET or NATURAL)
        2. If TICKET: try to fetch from ticket_mcp
        3. If fetch fails: fallback to synthetic ticket with warning
        4. If NATURAL: create synthetic ticket directly

        Args:
            request: Ticket ID (e.g., "PROJ-123") or natural request
                    (e.g., "Add login button")

        Returns:
            Ticket data dictionary with standard fields

        Examples:
            >>> # Ticket ID that exists
            >>> client = UnifiedMCPClient(mock_mcp)
            >>> ticket = client.get_ticket("PROJ-123")
            >>> ticket['_request_type']
            'ticket'

            >>> # Natural language request
            >>> ticket = client.get_ticket("Add login button")
            >>> ticket['_is_direct_request']
            True
            >>> ticket['_request_type']
            'natural'

            >>> # Ticket ID that doesn't exist (fallback)
            >>> ticket = client.get_ticket("PROJ-999")
            >>> ticket['_request_type']
            'natural'
        """
        # Parse request type
        try:
            request_type, cleaned_request = self.parser.parse(request)
        except ValueError as e:
            raise ValueError(f"Invalid request: {e}")

        if request_type == RequestType.TICKET:
            # Try to fetch actual ticket
            try:
                ticket = self.ticket_mcp.get_ticket(cleaned_request)
                # Mark as ticket type
                ticket["_request_type"] = "ticket"
                ticket["_is_direct_request"] = False
                return ticket

            except (ValueError, ConnectionError, KeyError) as e:
                # Ticket not found - treat as natural request with warning
                print(f"⚠️  Warning: Ticket '{cleaned_request}' not found: {e}")
                print(f"   Treating as natural language request...")
                return self.adapter.create_synthetic_ticket(cleaned_request)

        else:  # NATURAL request
            # Create synthetic ticket
            return self.adapter.create_synthetic_ticket(cleaned_request)

    def health_check(self) -> bool:
        """
        Check health of underlying ticket MCP

        Returns:
            True if ticket MCP is healthy, False otherwise
        """
        try:
            return self.ticket_mcp.health_check()
        except Exception:
            # If ticket MCP is down, we can still handle direct requests
            return True  # Consider healthy if we can create synthetic tickets

    def list_tickets(self, filter_params: Optional[Dict[str, Any]] = None) -> list:
        """
        List tickets from underlying MCP

        Args:
            filter_params: Optional filter parameters

        Returns:
            List of tickets

        Note: Direct requests are not listed here (they only exist as runs)
        """
        return self.ticket_mcp.list_tickets(filter_params)

    def get_ticket_history(self, ticket_id: str) -> list:
        """
        Get history for a ticket

        Args:
            ticket_id: Ticket identifier

        Returns:
            List of history entries

        Note: Synthetic tickets have no history
        """
        # Check if this is a synthetic ticket ID
        if ticket_id.startswith("DIRECT-"):
            return []  # No history for synthetic tickets

        return self.ticket_mcp.get_ticket_history(ticket_id)
