"""Unit tests for PipelineOrchestrator"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import sys

# Mock agents before importing PipelineOrchestrator to avoid pydantic dependency
mock_planner = MagicMock()
mock_implementer = MagicMock()
mock_reviewer = MagicMock()

with patch.dict(sys.modules, {
    'src.agents.planner_agent': mock_planner,
    'src.agents.implementer_agent': mock_implementer,
    'src.agents.reviewer_agent': mock_reviewer,
}):
    from src.orchestrator import PipelineOrchestrator

class TestPipelineOrchestratorUnit:
    """Unit tests for PipelineOrchestrator"""

    @pytest.fixture
    def mock_mcp_client(self):
        return Mock()

    @pytest.fixture
    def mock_artifact_manager(self):
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_mcp_client, mock_artifact_manager):
        return PipelineOrchestrator(
            mcp_client=mock_mcp_client,
            artifact_manager=mock_artifact_manager
        )

    def test_get_run_summary(self, orchestrator, mock_artifact_manager):
        """Test get_run_summary delegates to artifact_manager"""
        run_dir = Path("/mock/run/dir")
        expected_summary = {"status": "SUCCESS", "ticket_id": "PROJ-123"}
        mock_artifact_manager.load_run_summary.return_value = expected_summary

        summary = orchestrator.get_run_summary(run_dir)

        assert summary == expected_summary
        mock_artifact_manager.load_run_summary.assert_called_once_with(run_dir)

    def test_list_runs(self, orchestrator, mock_artifact_manager):
        """Test list_runs delegates to artifact_manager"""
        ticket_id = "PROJ-123"
        expected_runs = [Path("/mock/run/1"), Path("/mock/run/2")]
        mock_artifact_manager.list_runs.return_value = expected_runs

        runs = orchestrator.list_runs(ticket_id)

        assert runs == expected_runs
        mock_artifact_manager.list_runs.assert_called_once_with(ticket_id)

    def test_list_runs_no_ticket_id(self, orchestrator, mock_artifact_manager):
        """Test list_runs without ticket_id delegates to artifact_manager"""
        expected_runs = [Path("/mock/run/1"), Path("/mock/run/2")]
        mock_artifact_manager.list_runs.return_value = expected_runs

        runs = orchestrator.list_runs()

        assert runs == expected_runs
        mock_artifact_manager.list_runs.assert_called_once_with(None)
