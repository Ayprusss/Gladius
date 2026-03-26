"""Integration tests for the full pipeline"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import shutil

from src.orchestrator import PipelineOrchestrator
from src.mcp.mock_mcp import MockMCPClient
from src.utils.artifact_manager import ArtifactManager
from tests.fixtures.tickets import get_authentication_ticket


class TestPipelineIntegration:
    """Integration tests for full pipeline"""

    @pytest.fixture
    def temp_runs_dir(self, tmp_path):
        """Create temporary runs directory"""
        runs_dir = tmp_path / "test_runs"
        runs_dir.mkdir()
        yield runs_dir
        # Cleanup
        if runs_dir.exists():
            shutil.rmtree(runs_dir)

    @pytest.fixture
    def mock_claude_client(self):
        """Mock Claude client for integration tests"""
        client = Mock()
        return client

    @pytest.fixture
    def artifact_manager(self, temp_runs_dir):
        """Create artifact manager with temp directory"""
        return ArtifactManager(base_dir=str(temp_runs_dir))

    @pytest.fixture
    def mcp_client(self):
        """Create mock MCP client"""
        return MockMCPClient()

    def test_pipeline_end_to_end_mock(
        self,
        mock_claude_client,
        artifact_manager,
        mcp_client
    ):
        """Test full pipeline with mocked Claude responses"""
        # Mock responses for each agent
        planner_response = {
            "summary": "Add JWT authentication to API",
            "assumptions": ["Using PyJWT library", "24h token expiry"],
            "plan": [
                "Create JWT token generation function",
                "Implement authentication middleware",
                "Add token validation to protected routes"
            ],
            "files_to_change": [
                {"path": "src/auth/jwt.py", "reason": "Token generation"},
                {"path": "src/middleware/auth.py", "reason": "Auth middleware"},
                {"path": "src/routes/api.py", "reason": "Apply middleware"}
            ],
            "test_plan": [
                "Test token generation",
                "Test valid token access",
                "Test invalid token rejection"
            ],
            "risks": ["Token security", "Performance overhead"]
        }

        implementer_response = {
            "changes": [
                {
                    "file": "src/auth/jwt.py",
                    "type": "create",
                    "description": "Created JWT utilities"
                },
                {
                    "file": "src/middleware/auth.py",
                    "type": "create",
                    "description": "Created auth middleware"
                }
            ],
            "patch": """--- /dev/null
+++ b/src/auth/jwt.py
@@ -0,0 +1,10 @@
+import jwt
+
+def generate_token(user_id):
+    return jwt.encode({'user_id': user_id}, 'secret', algorithm='HS256')
""",
            "notes": "Implemented basic JWT authentication",
            "tests_added_or_updated": ["tests/test_auth.py"]
        }

        reviewer_response_approve = {
            "review_summary": "Implementation looks good. All requirements met.",
            "issues": [],
            "suggested_changes": [],
            "verdict": "APPROVE"
        }

        # Configure mock to return responses in sequence
        mock_claude_client.invoke.side_effect = [
            planner_response,
            implementer_response,
            reviewer_response_approve
        ]

        # Create orchestrator
        orchestrator = PipelineOrchestrator(
            mcp_client=mcp_client,
            artifact_manager=artifact_manager,
            max_review_iterations=2
        )
        orchestrator.claude_client = mock_claude_client

        # Run pipeline
        summary = orchestrator.run_pipeline(
            ticket_id="PROJ-123",
            model="sonnet"
        )

        # Verify summary
        assert summary["status"] == "SUCCESS"
        assert summary["approved"] is True
        assert summary["iterations"] == 1
        assert summary["ticket_id"] == "PROJ-123"
        assert summary["files_changed"] == 2

        # Verify artifacts were created
        run_dir = Path(summary["run_directory"])
        assert run_dir.exists()
        assert (run_dir / "ticket.json").exists()
        assert (run_dir / "planner" / "plan.json").exists()
        assert (run_dir / "implementer" / "implementation_v1.json").exists()
        assert (run_dir / "reviewer" / "review_v1.json").exists()
        assert (run_dir / "patches" / "changes_v1.patch").exists()
        assert (run_dir / "summary.json").exists()

        # Verify Claude was called 3 times (planner, implementer, reviewer)
        assert mock_claude_client.invoke.call_count == 3

    def test_pipeline_with_review_cycle(
        self,
        mock_claude_client,
        artifact_manager,
        mcp_client
    ):
        """Test pipeline with review requesting changes and resubmission"""
        planner_response = {
            "summary": "Add authentication",
            "assumptions": [],
            "plan": ["Step 1"],
            "files_to_change": [{"path": "auth.py", "reason": "Auth"}],
            "test_plan": ["Test 1"],
            "risks": []
        }

        implementer_response_v1 = {
            "changes": [{"file": "auth.py", "type": "create", "description": "Added"}],
            "patch": "--- patch v1 ---",
            "notes": "Initial implementation",
            "tests_added_or_updated": []
        }

        reviewer_response_changes = {
            "review_summary": "Security issue found",
            "issues": [
                {
                    "severity": "critical",
                    "file": "auth.py",
                    "line": 10,
                    "description": "Hardcoded secret",
                    "suggestion": "Use environment variable"
                }
            ],
            "suggested_changes": ["Move secret to config"],
            "verdict": "REQUEST_CHANGES"
        }

        implementer_response_v2 = {
            "changes": [{"file": "auth.py", "type": "modify", "description": "Fixed security"}],
            "patch": "--- patch v2 ---",
            "notes": "Fixed security issue",
            "tests_added_or_updated": []
        }

        reviewer_response_approve = {
            "review_summary": "All issues resolved",
            "issues": [],
            "suggested_changes": [],
            "verdict": "APPROVE"
        }

        # Configure mock responses
        mock_claude_client.invoke.side_effect = [
            planner_response,
            implementer_response_v1,
            reviewer_response_changes,
            implementer_response_v2,
            reviewer_response_approve
        ]

        # Create orchestrator
        orchestrator = PipelineOrchestrator(
            mcp_client=mcp_client,
            artifact_manager=artifact_manager,
            max_review_iterations=2
        )
        orchestrator.claude_client = mock_claude_client

        # Run pipeline
        summary = orchestrator.run_pipeline(
            ticket_id="PROJ-123",
            model="sonnet"
        )

        # Verify summary
        assert summary["status"] == "SUCCESS"
        assert summary["approved"] is True
        assert summary["iterations"] == 2

        # Verify both iterations were saved
        run_dir = Path(summary["run_directory"])
        assert (run_dir / "implementer" / "implementation_v1.json").exists()
        assert (run_dir / "implementer" / "implementation_v2.json").exists()
        assert (run_dir / "reviewer" / "review_v1.json").exists()
        assert (run_dir / "reviewer" / "review_v2.json").exists()

        # Verify Claude was called 5 times
        assert mock_claude_client.invoke.call_count == 5

    def test_pipeline_max_iterations_reached(
        self,
        mock_claude_client,
        artifact_manager,
        mcp_client
    ):
        """Test pipeline stops after max iterations"""
        planner_response = {
            "summary": "Test",
            "assumptions": [],
            "plan": ["Step 1"],
            "files_to_change": [],
            "test_plan": [],
            "risks": []
        }

        implementer_response = {
            "changes": [],
            "patch": "",
            "notes": "",
            "tests_added_or_updated": []
        }

        reviewer_response_changes = {
            "review_summary": "Issues",
            "issues": [
                {
                    "severity": "critical",
                    "file": "test.py",
                    "line": 1,
                    "description": "Problem",
                    "suggestion": "Fix"
                }
            ],
            "suggested_changes": [],
            "verdict": "REQUEST_CHANGES"
        }

        # Always request changes
        mock_claude_client.invoke.side_effect = [
            planner_response,
            implementer_response,
            reviewer_response_changes,
            implementer_response,
            reviewer_response_changes,
        ]

        # Create orchestrator with max 2 iterations
        orchestrator = PipelineOrchestrator(
            mcp_client=mcp_client,
            artifact_manager=artifact_manager,
            max_review_iterations=2
        )
        orchestrator.claude_client = mock_claude_client

        # Run pipeline
        summary = orchestrator.run_pipeline(
            ticket_id="PROJ-123",
            model="sonnet"
        )

        # Verify max iterations reached
        assert summary["status"] == "MAX_ITERATIONS_REACHED"
        assert summary["approved"] is False
        assert summary["iterations"] == 2
        assert summary["critical_issues"] > 0


class TestArtifactManager:
    """Integration tests for artifact manager"""

    @pytest.fixture
    def temp_runs_dir(self, tmp_path):
        """Create temporary runs directory"""
        runs_dir = tmp_path / "test_runs"
        runs_dir.mkdir()
        yield runs_dir
        if runs_dir.exists():
            shutil.rmtree(runs_dir)

    def test_create_run_structure(self, temp_runs_dir):
        """Test run directory structure creation"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        run_dir = manager.create_run("PROJ-123")

        assert run_dir.exists()
        assert (run_dir / "planner").exists()
        assert (run_dir / "implementer").exists()
        assert (run_dir / "reviewer").exists()
        assert (run_dir / "patches").exists()

    def test_save_and_load_artifacts(self, temp_runs_dir):
        """Test saving and loading artifacts"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))
        manager.create_run("PROJ-123")

        # Save artifacts
        ticket_data = {"id": "PROJ-123", "title": "Test"}
        planner_output = {"summary": "Test plan"}

        manager.save_ticket_data(ticket_data)
        manager.save_planner_output(planner_output)

        # Verify files exist
        run_dir = manager.get_run_dir()
        assert (run_dir / "ticket.json").exists()
        assert (run_dir / "planner" / "plan.json").exists()

    def test_list_runs(self, temp_runs_dir):
        """Test listing runs"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        # Create multiple runs
        manager.create_run("PROJ-123")
        manager.create_run("PROJ-456")
        manager.create_run("PROJ-123")  # Another run for same ticket

        # List all runs
        all_runs = manager.list_runs()
        assert len(all_runs) == 3

        # List filtered by ticket
        proj_123_runs = manager.list_runs("PROJ-123")
        assert len(proj_123_runs) == 2
        assert all("PROJ-123" in str(run) for run in proj_123_runs)

    def test_cleanup_old_runs(self, temp_runs_dir):
        """Test cleanup of old runs"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        # Create 5 runs
        for i in range(5):
            manager.create_run(f"PROJ-{i}")

        # Keep only 2 most recent
        deleted = manager.cleanup_old_runs(keep_last=2)

        assert deleted == 3
        remaining = manager.list_runs()
        assert len(remaining) == 2
