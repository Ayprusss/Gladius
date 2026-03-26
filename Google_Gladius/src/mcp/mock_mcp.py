"""Mock MCP implementation for testing without real Jira connection"""
from typing import Dict, Any
from .mcp_client import MCPClient


class MockMCPClient(MCPClient):
    """Mock MCP client that returns sample ticket data"""

    # Sample ticket data
    SAMPLE_TICKETS = {
        "PROJ-123": {
            "key": "PROJ-123",
            "title": "Add user authentication to API",
            "description": """
Implement JWT-based authentication for the API to secure endpoints.

Requirements:
- Users should be able to login with username/password
- JWT tokens should be returned on successful login
- Protected endpoints should validate JWT tokens
- Tokens should expire after 24 hours
- Include proper error handling for invalid credentials
            """.strip(),
            "type": "feature",
            "priority": "high",
            "status": "open",
            "acceptance_criteria": [
                "POST /api/login endpoint accepts username and password",
                "Returns JWT token on successful authentication",
                "Protected endpoints return 401 for missing/invalid tokens",
                "Tokens expire after 24 hours",
                "Error messages are clear and helpful"
            ],
            "comments": [
                {
                    "author": "product-manager",
                    "text": "This is needed for the Q1 release. Please prioritize."
                },
                {
                    "author": "tech-lead",
                    "text": "Consider using PyJWT library. Make sure to use environment variables for secrets."
                }
            ],
            "related_tickets": ["PROJ-100", "PROJ-110"]
        },
        "PROJ-456": {
            "key": "PROJ-456",
            "title": "Fix memory leak in data processing pipeline",
            "description": """
The data processing pipeline is experiencing memory leaks when processing large files.
Memory usage grows unbounded and eventually causes OOM errors.

Steps to reproduce:
1. Process file larger than 1GB
2. Monitor memory usage
3. Observe memory not being released after processing

Expected: Memory should be released after processing each chunk
Actual: Memory accumulates and is never released
            """.strip(),
            "type": "bug",
            "priority": "critical",
            "status": "open",
            "acceptance_criteria": [
                "Process 5GB file without memory leak",
                "Memory usage stays under 500MB",
                "Add memory profiling tests",
                "Document memory management approach"
            ],
            "comments": [
                {
                    "author": "developer",
                    "text": "I suspect the issue is in the file reader. We might be holding references to processed chunks."
                }
            ],
            "related_tickets": []
        },
        "PROJ-789": {
            "key": "PROJ-789",
            "title": "Refactor database query layer for better performance",
            "description": """
Current database query layer has performance issues:
- N+1 query problems in several endpoints
- Missing indexes on frequently queried columns
- Inefficient ORM usage patterns

Goal: Refactor to improve query performance by 50%
            """.strip(),
            "type": "improvement",
            "priority": "medium",
            "status": "open",
            "acceptance_criteria": [
                "Identify and fix all N+1 query issues",
                "Add database indexes where needed",
                "Implement query result caching",
                "Reduce API response times by 50%",
                "Add performance monitoring"
            ],
            "comments": [],
            "related_tickets": ["PROJ-780", "PROJ-790"]
        }
    }

    def __init__(self):
        """Initialize mock MCP client"""
        pass

    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Get sample ticket data

        Args:
            ticket_id: Ticket identifier

        Returns:
            Sample ticket data

        Raises:
            ValueError: If ticket ID not found in sample data
        """
        if ticket_id not in self.SAMPLE_TICKETS:
            raise ValueError(
                f"Ticket {ticket_id} not found in mock data. "
                f"Available tickets: {', '.join(self.SAMPLE_TICKETS.keys())}"
            )

        return self.SAMPLE_TICKETS[ticket_id]

    def health_check(self) -> bool:
        """Mock health check always returns True"""
        return True

    def list_available_tickets(self) -> list:
        """
        List all available sample tickets

        Returns:
            List of ticket IDs
        """
        return list(self.SAMPLE_TICKETS.keys())
