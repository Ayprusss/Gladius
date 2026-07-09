"""Unit tests for ArtifactManager"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
from src.utils.artifact_manager import ArtifactManager

class TestArtifactManager:
    """Unit tests for ArtifactManager"""

    @pytest.fixture
    def temp_runs_dir(self, tmp_path):
        """Create temporary runs directory"""
        runs_dir = tmp_path / "test_runs"
        runs_dir.mkdir()
        return runs_dir

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
        from datetime import datetime
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        with patch('src.utils.artifact_manager.datetime') as mock_date:
            mock_date.now.side_effect = [
                datetime(2023, 1, 1, 12, 0, 0),
                datetime(2023, 1, 1, 12, 0, 1),
                datetime(2023, 1, 1, 12, 0, 2),
            ]
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

    def test_cleanup_old_runs_error_handling(self, temp_runs_dir):
        """Test cleanup error handling when deletion fails"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        # Create 3 runs
        for i in range(3):
            manager.create_run(f"PROJ-{i}")

        # Mock shutil.rmtree to fail for the first run to be deleted
        with patch("shutil.rmtree") as mock_rmtree:
            # We want to keep 1, so 2 will be deleted.
            # Make one fail and one succeed.
            mock_rmtree.side_effect = [Exception("Permission denied"), None]

            # This should try to delete 2 runs
            deleted = manager.cleanup_old_runs(keep_last=1)

            # Only one should be reported as deleted
            assert deleted == 1
            # shutil.rmtree should have been called twice
            assert mock_rmtree.call_count == 2

    def test_cleanup_old_runs_all_fail(self, temp_runs_dir):
        """Test cleanup when all deletions fail"""
        manager = ArtifactManager(base_dir=str(temp_runs_dir))

        # Create 3 runs
        for i in range(3):
            manager.create_run(f"PROJ-{i}")

        # Mock shutil.rmtree to fail for all
        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = Exception("General Error")

            # This should try to delete 2 runs
            deleted = manager.cleanup_old_runs(keep_last=1)

            assert deleted == 0
            assert mock_rmtree.call_count == 2
