"""Convert natural language requests to synthetic ticket format"""
from datetime import datetime
from typing import Dict, Any, Optional
from .type_detector import RequestTypeDetector


class DirectRequestAdapter:
    """Convert natural language requests to synthetic ticket format"""

    def __init__(self, ticket_prefix: str = "DIRECT"):
        """
        Initialize DirectRequestAdapter

        Args:
            ticket_prefix: Prefix for synthetic ticket IDs (default: "DIRECT")
        """
        self.ticket_prefix = ticket_prefix
        self.type_detector = RequestTypeDetector()

    def create_synthetic_ticket(
        self,
        request: str,
        ticket_type: Optional[str] = None,
        priority: str = "medium",
        suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create synthetic ticket from natural request

        Generates a ticket in the standard format expected by the pipeline,
        with auto-detection of ticket type based on keywords.

        Args:
            request: Natural language request
            ticket_type: Override auto-detection (feature, bug, improvement)
            priority: Ticket priority (default: medium)
            suffix: Optional suffix for the ticket ID to ensure uniqueness

        Returns:
            Synthetic ticket in standard format

        Example:
            >>> adapter = DirectRequestAdapter()
            >>> ticket = adapter.create_synthetic_ticket("Add login button to homepage")
            >>> ticket['title']
            'Add login button to homepage'
            >>> ticket['type']
            'feature'
            >>> ticket['_is_direct_request']
            True
        """
        # Validate request
        if not request or not request.strip():
            raise ValueError("Request cannot be empty")

        request = request.strip()

        # Generate unique ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if suffix:
            ticket_id = f"{self.ticket_prefix}-{timestamp}-{suffix}"
        else:
            ticket_id = f"{self.ticket_prefix}-{timestamp}"

        # Auto-detect type if not specified
        if ticket_type is None:
            ticket_type = self.type_detector.detect_type(request)

        # Extract title (first 100 chars or first sentence)
        title = self._extract_title(request)

        # Create synthetic ticket
        return {
            "key": ticket_id,
            "title": title,
            "description": request,  # Full request in description
            "type": ticket_type,
            "priority": priority,
            "status": "open",
            "acceptance_criteria": [],
            "comments": [],
            "related_tickets": [],
            "_is_direct_request": True,  # Flag for agents
            "_request_type": "natural"  # For tracking
        }

    def _extract_title(self, request: str, max_length: int = 100) -> str:
        """
        Extract title from request (first sentence or truncate)

        Args:
            request: Full request text
            max_length: Maximum title length

        Returns:
            Extracted title string

        Examples:
            >>> adapter = DirectRequestAdapter()
            >>> adapter._extract_title("Add login. This should be secure.")
            'Add login'

            >>> adapter._extract_title("Short request")
            'Short request'

            >>> adapter._extract_title("A" * 150)
            'AAAA... (truncated)'
        """
        # Try to get first sentence
        sentences = request.split('.')
        if sentences and len(sentences[0].strip()) <= max_length and sentences[0].strip():
            return sentences[0].strip()

        # Otherwise truncate at word boundary
        if len(request) <= max_length:
            return request

        # Truncate at last space before max_length
        truncated = request[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > 0:
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."

    def create_tickets_batch(
        self,
        requests: list[str],
        ticket_type: Optional[str] = None,
        priority: str = "medium"
    ) -> list[Dict[str, Any]]:
        """
        Create multiple synthetic tickets from a list of requests

        Args:
            requests: List of natural language requests
            ticket_type: Override auto-detection for all tickets
            priority: Priority for all tickets

        Returns:
            List of synthetic tickets

        Example:
            >>> adapter = DirectRequestAdapter()
            >>> tickets = adapter.create_tickets_batch(["Add login", "Fix bug"])
            >>> len(tickets)
            2
        """
        tickets = []
        for i, request in enumerate(requests):
            # Use index as suffix to ensure uniqueness within the batch
            # without needing to sleep between requests
            ticket = self.create_synthetic_ticket(
                request=request,
                ticket_type=ticket_type,
                priority=priority,
                suffix=str(i)
            )
            tickets.append(ticket)

        return tickets
