"""Parse and classify user requests (ticket ID vs natural language)"""
import re
from enum import Enum
from typing import Tuple


class RequestType(Enum):
    """Type of user request"""
    TICKET = "ticket"
    NATURAL = "natural"


class RequestParser:
    """Parse and classify user requests"""

    # Ticket ID pattern: PROJ-123, ABC-45, etc.
    # Matches: uppercase letters, dash, digits
    TICKET_PATTERN = r'^[A-Z]+-\d+$'

    @staticmethod
    def parse(input_string: str) -> Tuple[RequestType, str]:
        """
        Determine if input is ticket ID or natural request

        Args:
            input_string: User input (ticket ID or natural request)

        Returns:
            Tuple of (RequestType, cleaned_input)

        Examples:
            >>> RequestParser.parse("PROJ-123")
            (RequestType.TICKET, "PROJ-123")

            >>> RequestParser.parse("Add login button")
            (RequestType.NATURAL, "Add login button")

            >>> RequestParser.parse("  TASK-456  ")
            (RequestType.TICKET, "TASK-456")

            >>> RequestParser.parse("Fix the bug in auth.py")
            (RequestType.NATURAL, "Fix the bug in auth.py")
        """
        # Clean input
        cleaned = input_string.strip()

        # Empty string handling
        if not cleaned:
            raise ValueError("Request cannot be empty")

        # Check if it matches ticket ID pattern
        if re.match(RequestParser.TICKET_PATTERN, cleaned):
            return (RequestType.TICKET, cleaned)
        else:
            return (RequestType.NATURAL, cleaned)

    @staticmethod
    def is_ticket_id(input_string: str) -> bool:
        """
        Check if input looks like a ticket ID

        Args:
            input_string: Input to check

        Returns:
            True if input matches ticket ID pattern

        Examples:
            >>> RequestParser.is_ticket_id("PROJ-123")
            True

            >>> RequestParser.is_ticket_id("Add feature")
            False
        """
        cleaned = input_string.strip()
        return bool(re.match(RequestParser.TICKET_PATTERN, cleaned))
