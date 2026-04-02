"""Integration test for project_path feature"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestrator import PipelineOrchestrator
from src.mcp.mock_mcp import MockMCPClient
from src.utils.artifact_manager import ArtifactManager
from src.utils.path_resolver import ProjectPathResolver
from src.utils.path_validator import PathValidator


class TestProjectPathIntegration:
    """Test project path feature integration"""

    def test_path_validator_basic(self):
        """Test PathValidator works correctly"""
        # Test with current directory
        current_dir = Path.cwd()
        result = PathValidator.validate_project_path(current_dir)

        assert result.is_absolute()
        assert result.exists()
        assert result.is_dir()

    def test_path_validator_relative(self):
        """Test PathValidator converts relative to absolute"""
        result = PathValidator.validate_project_path(".")

        assert result.is_absolute()
        assert result == Path.cwd().resolve()

    def test_path_validator_invalid_raises(self):
        """Test PathValidator raises on invalid path"""
        with pytest.raises(ValueError, match="does not exist"):
            PathValidator.validate_project_path("/nonexistent/path/12345")

    def test_path_resolver_cli_priority(self):
        """Test ProjectPathResolver prioritizes CLI argument"""
        resolver = ProjectPathResolver()

        # CLI path should take priority
        result = resolver.resolve_project_path(
            cli_path=str(Path.cwd()),
            config_path="/some/config/path",
            use_cwd=True
        )

        assert result == Path.cwd().resolve()

    def test_path_resolver_cwd_fallback(self):
        """Test ProjectPathResolver falls back to CWD"""
        resolver = ProjectPathResolver()

        result = resolver.resolve_project_path(
            cli_path=None,
            config_path=None,
            use_cwd=True
        )

        assert result == Path.cwd().resolve()

    def test_orchestrator_accepts_project_path(self):
        """Test orchestrator accepts project_path parameter"""
        mcp_client = MockMCPClient()
        artifact_manager = MagicMock()

        orchestrator = PipelineOrchestrator(
            mcp_client=mcp_client,
            artifact_manager=artifact_manager
        )

        # Mock the agent executions
        orchestrator.planner.execute = Mock(return_value=Mock(
            summary="Test plan",
            plan=["Step 1", "Step 2"],
            files_to_change=[],
            test_strategy="Test all",
            assumptions=[],
            risks=[],
            model_dump=lambda: {
                "summary": "Test plan",
                "plan": ["Step 1", "Step 2"],
                "files_to_change": [],
                "test_strategy": "Test all",
                "assumptions": [],
                "risks": []
            }
        ))

        orchestrator.implementer.execute = Mock(return_value=Mock(
            changes=[],
            patch="",
            notes="",
            tests_added_or_updated=[],
            model_dump=lambda: {
                "changes": [],
                "patch": "",
                "notes": "",
                "tests_added_or_updated": []
            }
        ))

        orchestrator.reviewer.execute = Mock(return_value=Mock(
            verdict="APPROVE",
            issues=[],
            suggested_changes=[],
            model_dump=lambda: {
                "verdict": "APPROVE",
                "issues": [],
                "suggested_changes": []
            }
        ))

        artifact_manager.create_run = Mock(return_value=Path("/tmp/test"))
        artifact_manager.save_ticket_data = Mock()
        artifact_manager.save_planner_output = Mock()
        artifact_manager.save_implementer_output = Mock()
        artifact_manager.save_reviewer_output = Mock()
        artifact_manager.save_run_summary = Mock()

        # Call run_pipeline with project_path
        project_path = Path.cwd()
        summary = orchestrator.run_pipeline(
            request="PROJ-123",
            model="sonnet",
            project_path=project_path
        )

        # Verify project_path is in summary
        assert "project_path" in summary
        assert summary["project_path"] == str(project_path)
        assert summary["status"] == "SUCCESS"

    def test_agent_context_includes_project_path(self):
        """Test that agent contexts include project_path"""
        from src.agents.planner_agent import PlannerAgent
        from src.agents.implementer_agent import ImplementerAgent
        from src.agents.reviewer_agent import ReviewerAgent

        mock_client = Mock()

        # Test planner agent
        planner = PlannerAgent(mock_client)
        context = {
            "ticket": {
                "key": "TEST-1",
                "title": "Test",
                "description": "Test desc"
            },
            "project_path": "/path/to/project",
            "project_path_absolute": "/absolute/path/to/project"
        }
        message = planner.build_user_message(context)
        assert "Project Context" in message
        assert "/path/to/project" in message

        # Test implementer agent
        from src.schemas.planner_schema import PlannerOutput
        implementer = ImplementerAgent(mock_client)

        plan_output = PlannerOutput(
            summary="Test plan",
            plan=["Step 1"],
            files_to_change=[],
            test_strategy="Test",
            assumptions=[],
            risks=[]
        )

        impl_context = {
            "ticket": {"key": "TEST-1", "title": "Test", "description": "Test"},
            "plan": plan_output,
            "project_path": "/path/to/project",
            "project_path_absolute": "/absolute/path/to/project"
        }
        impl_message = implementer.build_user_message(impl_context)
        assert "Project Context" in impl_message
        assert "/path/to/project" in impl_message

        # Test reviewer agent
        from src.schemas.implementer_schema import ImplementerOutput
        reviewer = ReviewerAgent(mock_client)

        impl_output = ImplementerOutput(
            changes=[],
            patch="",
            notes="",
            tests_added_or_updated=[]
        )

        review_context = {
            "ticket": {"key": "TEST-1", "title": "Test", "description": "Test"},
            "plan": plan_output,
            "implementation": impl_output,
            "project_path": "/path/to/project",
            "project_path_absolute": "/absolute/path/to/project"
        }
        review_message = reviewer.build_user_message(review_context)
        assert "Project Context" in review_message
        assert "/path/to/project" in review_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
