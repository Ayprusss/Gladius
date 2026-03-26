"""Sample ticket fixtures for testing"""
from typing import Dict, Any


def get_authentication_ticket() -> Dict[str, Any]:
    """Feature ticket: Add user authentication"""
    return {
        "id": "PROJ-123",
        "title": "Add user authentication to API",
        "type": "feature",
        "description": """
We need to add JWT-based authentication to our REST API to secure user endpoints.

Requirements:
- Implement JWT token generation on login
- Add middleware to validate tokens on protected routes
- Store user sessions securely
- Support token refresh mechanism
- Add logout functionality

Acceptance Criteria:
- Users can log in with email/password and receive a JWT token
- Protected endpoints return 401 for invalid/missing tokens
- Tokens expire after 24 hours
- Refresh tokens work correctly
- Unit tests cover all auth flows
        """.strip(),
        "priority": "high",
        "labels": ["security", "backend", "api"],
        "assignee": "dev-team",
        "created_at": "2024-01-15T10:30:00Z"
    }


def get_memory_leak_ticket() -> Dict[str, Any]:
    """Bug ticket: Fix memory leak"""
    return {
        "id": "PROJ-456",
        "title": "Fix memory leak in background job processor",
        "type": "bug",
        "description": """
Production monitoring shows memory usage growing unbounded in the background job processor.

Symptoms:
- Memory usage increases by ~100MB per hour
- Process needs restart every 12 hours to avoid OOM
- Observed in production and staging environments

Investigation:
- Profiling shows objects not being garbage collected
- Likely related to event listener registration
- May be in the job queue consumer

Steps to Reproduce:
1. Start background job processor
2. Run for 6+ hours with normal job load
3. Monitor memory usage via system metrics

Expected: Memory usage should stabilize after initial ramp-up
Actual: Memory grows continuously until process crashes
        """.strip(),
        "priority": "critical",
        "labels": ["bug", "performance", "backend"],
        "assignee": "senior-dev",
        "created_at": "2024-01-14T08:15:00Z"
    }


def get_refactoring_ticket() -> Dict[str, Any]:
    """Improvement ticket: Refactor database layer"""
    return {
        "id": "PROJ-789",
        "title": "Refactor database layer to use repository pattern",
        "type": "improvement",
        "description": """
Current database access is scattered across the codebase with direct ORM queries.
This makes testing difficult and violates separation of concerns.

Goals:
- Introduce repository pattern for data access
- Create interfaces for each domain entity
- Move all database queries into repository classes
- Make repositories easily mockable for tests

Benefits:
- Better testability (can mock repositories)
- Clearer separation of concerns
- Easier to swap ORM or database in future
- Consistent data access patterns

Scope:
- User repository
- Product repository
- Order repository
- Transaction repository

Non-Goals:
- Changing the database schema
- Performance optimization (separate ticket)
        """.strip(),
        "priority": "medium",
        "labels": ["refactoring", "backend", "architecture"],
        "assignee": "dev-team",
        "created_at": "2024-01-16T14:20:00Z"
    }


def get_simple_feature_ticket() -> Dict[str, Any]:
    """Simple feature ticket for quick testing"""
    return {
        "id": "PROJ-001",
        "title": "Add email validation to user registration",
        "type": "feature",
        "description": """
Add proper email validation to the user registration endpoint.

Requirements:
- Validate email format using regex
- Check for common typos (e.g., @gmial.com)
- Return clear error message for invalid emails
- Add unit tests for validation logic

Acceptance Criteria:
- Invalid emails are rejected with 400 status
- Error message clearly indicates email format issue
- Tests cover edge cases (empty, invalid format, etc.)
        """.strip(),
        "priority": "low",
        "labels": ["feature", "backend", "validation"],
        "assignee": "junior-dev",
        "created_at": "2024-01-17T09:00:00Z"
    }


def get_documentation_ticket() -> Dict[str, Any]:
    """Documentation ticket"""
    return {
        "id": "PROJ-999",
        "title": "Document API authentication flow",
        "type": "documentation",
        "description": """
Create comprehensive documentation for the API authentication system.

Contents needed:
- Authentication flow diagram
- How to obtain access tokens
- Token refresh mechanism
- Error codes and handling
- Code examples in Python and JavaScript
- Security best practices

Target audience: External API consumers and new team members

Format: Markdown documentation in docs/api/authentication.md
        """.strip(),
        "priority": "medium",
        "labels": ["documentation", "api"],
        "assignee": "tech-writer",
        "created_at": "2024-01-18T11:30:00Z"
    }


# Registry of all fixtures
TICKET_FIXTURES = {
    "PROJ-123": get_authentication_ticket,
    "PROJ-456": get_memory_leak_ticket,
    "PROJ-789": get_refactoring_ticket,
    "PROJ-001": get_simple_feature_ticket,
    "PROJ-999": get_documentation_ticket,
}


def get_ticket_fixture(ticket_id: str) -> Dict[str, Any]:
    """
    Get a ticket fixture by ID

    Args:
        ticket_id: Ticket identifier

    Returns:
        Ticket data dictionary

    Raises:
        KeyError: If ticket ID not found
    """
    if ticket_id not in TICKET_FIXTURES:
        raise KeyError(f"No fixture found for ticket: {ticket_id}")

    return TICKET_FIXTURES[ticket_id]()


def list_ticket_fixtures() -> list[str]:
    """
    List all available ticket fixture IDs

    Returns:
        List of ticket IDs
    """
    return list(TICKET_FIXTURES.keys())
