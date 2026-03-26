"""Unit tests for agent classes"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.agents.planner_agent import PlannerAgent
from src.agents.implementer_agent import ImplementerAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.schemas.planner_schema import PlannerOutput
from src.schemas.implementer_schema import ImplementerOutput
from src.schemas.reviewer_schema import ReviewerOutput
from tests.fixtures.tickets import get_authentication_ticket


class TestPlannerAgent:
    """Tests for PlannerAgent"""

    @pytest.fixture
    def mock_claude_client(self):
        """Mock Claude client"""
        client = Mock()
        client.invoke = Mock()
        return client

    @pytest.fixture
    def planner_agent(self, mock_claude_client):
        """Create planner agent with mocked client"""
        return PlannerAgent(mock_claude_client)

    def test_planner_agent_initialization(self, planner_agent):
        """Test planner agent initializes correctly"""
        assert planner_agent is not None
        assert planner_agent.max_retries == 3
        assert planner_agent.base_delay == 2.0

    def test_get_system_prompt(self, planner_agent):
        """Test system prompt is loaded"""
        prompt = planner_agent.get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0
        assert "planner" in prompt.lower() or "plan" in prompt.lower()

    def test_get_output_schema(self, planner_agent):
        """Test output schema is correct"""
        schema = planner_agent.get_output_schema()
        assert schema == PlannerOutput

    def test_build_user_message(self, planner_agent):
        """Test user message building"""
        ticket = get_authentication_ticket()
        context = {"ticket": ticket}

        message = planner_agent.build_user_message(context)

        assert message is not None
        assert ticket["id"] in message
        assert ticket["title"] in message
        assert ticket["description"] in message

    def test_execute_success(self, mock_claude_client, planner_agent):
        """Test successful execution"""
        # Mock Claude response
        mock_response = {
            "summary": "Add JWT authentication",
            "assumptions": ["Using existing user database"],
            "plan": ["Step 1", "Step 2"],
            "files_to_change": [
                {"path": "auth.py", "reason": "Add auth logic"}
            ],
            "test_plan": ["Test login"],
            "risks": ["Security concerns"]
        }
        mock_claude_client.invoke.return_value = mock_response

        # Execute
        ticket = get_authentication_ticket()
        context = {"ticket": ticket}
        result = planner_agent.execute(context)

        # Verify
        assert isinstance(result, PlannerOutput)
        assert result.summary == "Add JWT authentication"
        assert len(result.plan) == 2
        mock_claude_client.invoke.assert_called_once()

    def test_execute_with_retry(self, mock_claude_client, planner_agent):
        """Test execution with validation error and retry"""
        # First call fails validation, second succeeds
        invalid_response = {"summary": "Test"}  # Missing required fields
        valid_response = {
            "summary": "Add JWT authentication",
            "assumptions": [],
            "plan": ["Step 1"],
            "files_to_change": [],
            "test_plan": [],
            "risks": []
        }

        mock_claude_client.invoke.side_effect = [invalid_response, valid_response]

        # Execute
        ticket = get_authentication_ticket()
        context = {"ticket": ticket}

        with patch('time.sleep'):  # Skip actual sleep
            result = planner_agent.execute(context)

        # Verify retry happened
        assert isinstance(result, PlannerOutput)
        assert mock_claude_client.invoke.call_count == 2


class TestImplementerAgent:
    """Tests for ImplementerAgent"""

    @pytest.fixture
    def mock_claude_client(self):
        """Mock Claude client"""
        client = Mock()
        client.invoke = Mock()
        return client

    @pytest.fixture
    def implementer_agent(self, mock_claude_client):
        """Create implementer agent with mocked client"""
        return ImplementerAgent(mock_claude_client)

    def test_implementer_agent_initialization(self, implementer_agent):
        """Test implementer agent initializes correctly"""
        assert implementer_agent is not None

    def test_get_output_schema(self, implementer_agent):
        """Test output schema is correct"""
        schema = implementer_agent.get_output_schema()
        assert schema == ImplementerOutput

    def test_build_user_message_initial(self, implementer_agent):
        """Test user message for initial implementation"""
        ticket = get_authentication_ticket()
        plan = {
            "summary": "Add auth",
            "plan": ["Step 1", "Step 2"],
            "files_to_change": []
        }
        context = {
            "ticket": ticket,
            "plan": plan,
            "iteration": 1
        }

        message = implementer_agent.build_user_message(context)

        assert message is not None
        assert ticket["id"] in message
        assert "Step 1" in message
        assert "review_feedback" not in message.lower()

    def test_build_user_message_with_feedback(self, implementer_agent):
        """Test user message includes review feedback"""
        ticket = get_authentication_ticket()
        plan = {"summary": "Add auth", "plan": ["Step 1"]}
        review_feedback = {
            "verdict": "REQUEST_CHANGES",
            "issues": [
                {
                    "severity": "critical",
                    "file": "auth.py",
                    "description": "Security issue",
                    "suggestion": "Fix this"
                }
            ],
            "suggested_changes": ["Change X"]
        }
        context = {
            "ticket": ticket,
            "plan": plan,
            "iteration": 2,
            "review_feedback": review_feedback
        }

        message = implementer_agent.build_user_message(context)

        assert "Security issue" in message
        assert "Fix this" in message


class TestReviewerAgent:
    """Tests for ReviewerAgent"""

    @pytest.fixture
    def mock_claude_client(self):
        """Mock Claude client"""
        client = Mock()
        client.invoke = Mock()
        return client

    @pytest.fixture
    def reviewer_agent(self, mock_claude_client):
        """Create reviewer agent with mocked client"""
        return ReviewerAgent(mock_claude_client)

    def test_reviewer_agent_initialization(self, reviewer_agent):
        """Test reviewer agent initializes correctly"""
        assert reviewer_agent is not None

    def test_get_output_schema(self, reviewer_agent):
        """Test output schema is correct"""
        schema = reviewer_agent.get_output_schema()
        assert schema == ReviewerOutput

    def test_build_user_message(self, reviewer_agent):
        """Test user message building"""
        ticket = get_authentication_ticket()
        plan = {"summary": "Add auth", "plan": ["Step 1"]}
        implementation = {
            "changes": [{"file": "auth.py", "type": "create", "description": "Added"}],
            "patch": "--- diff here ---",
            "notes": "Implementation notes"
        }
        context = {
            "ticket": ticket,
            "plan": plan,
            "implementation": implementation
        }

        message = reviewer_agent.build_user_message(context)

        assert message is not None
        assert ticket["id"] in message
        assert "auth.py" in message
        assert "--- diff here ---" in message

    def test_execute_approve(self, mock_claude_client, reviewer_agent):
        """Test execution with approval verdict"""
        mock_response = {
            "review_summary": "Looks good",
            "issues": [],
            "suggested_changes": [],
            "verdict": "APPROVE"
        }
        mock_claude_client.invoke.return_value = mock_response

        ticket = get_authentication_ticket()
        context = {
            "ticket": ticket,
            "plan": {"summary": "Test"},
            "implementation": {"changes": [], "patch": "", "notes": ""}
        }

        result = reviewer_agent.execute(context)

        assert isinstance(result, ReviewerOutput)
        assert result.verdict == "APPROVE"
        assert len(result.issues) == 0

    def test_execute_request_changes(self, mock_claude_client, reviewer_agent):
        """Test execution with changes requested"""
        mock_response = {
            "review_summary": "Issues found",
            "issues": [
                {
                    "severity": "critical",
                    "file": "auth.py",
                    "line": 10,
                    "description": "Problem",
                    "suggestion": "Fix it"
                }
            ],
            "suggested_changes": ["Change X"],
            "verdict": "REQUEST_CHANGES"
        }
        mock_claude_client.invoke.return_value = mock_response

        ticket = get_authentication_ticket()
        context = {
            "ticket": ticket,
            "plan": {"summary": "Test"},
            "implementation": {"changes": [], "patch": "", "notes": ""}
        }

        result = reviewer_agent.execute(context)

        assert isinstance(result, ReviewerOutput)
        assert result.verdict == "REQUEST_CHANGES"
        assert len(result.issues) == 1
        assert result.issues[0].severity == "critical"
