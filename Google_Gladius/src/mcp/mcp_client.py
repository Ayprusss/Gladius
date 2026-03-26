"""MCP Client interface for fetching ticket data"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPClient(ABC):
    """Abstract interface for MCP client implementations"""

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch ticket data from MCP server

        Args:
            ticket_id: Ticket identifier (e.g., "PROJ-123")

        Returns:
            Dictionary containing ticket data

        Raises:
            ConnectionError: If MCP server is unreachable
            ValueError: If ticket not found
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if MCP server is available

        Returns:
            True if server is healthy, False otherwise
        """
        pass
