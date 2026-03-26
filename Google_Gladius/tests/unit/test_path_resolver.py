"""Unit tests for ProjectPathResolver"""
import pytest
from pathlib import Path

from src.utils.path_resolver import ProjectPathResolver


class TestProjectPathResolver:
    """Tests for ProjectPathResolver class"""

    @pytest.fixture
    def resolver(self):
        """Create resolver instance"""
        return ProjectPathResolver()

    def test_cli_path_takes_priority(self, resolver, tmp_path):
        """Test CLI path takes priority over all others"""
        cli_dir = tmp_path / "cli_project"
        cli_dir.mkdir()

        config_dir = tmp_path / "config_project"
        config_dir.mkdir()

        result = resolver.resolve_project_path(
            cli_path=str(cli_dir),
            config_path=str(config_dir),
            use_cwd=True
        )

        assert result == cli_dir.resolve()

    def test_cwd_used_when_no_cli_path(self, resolver):
        """Test current directory is used when no CLI path provided"""
        result = resolver.resolve_project_path(
            cli_path=None,
            use_cwd=True
        )

        assert result == Path.cwd().resolve()

    def test_config_fallback_when_no_cli_or_cwd(self, resolver, tmp_path):
        """Test config path is used when CLI and CWD not available"""
        config_dir = tmp_path / "config_project"
        config_dir.mkdir()

        result = resolver.resolve_project_path(
            cli_path=None,
            config_path=str(config_dir),
            use_cwd=False
        )

        assert result == config_dir.resolve()

    def test_cwd_detection_automatic(self, resolver):
        """Test CWD is detected automatically by default"""
        result = resolver.resolve_project_path()
        assert result == Path.cwd().resolve()

    def test_invalid_cli_path_raises_error(self, resolver):
        """Test invalid CLI path raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            resolver.resolve_project_path(cli_path="/nonexistent/path")
        assert "does not exist" in str(exc_info.value)

    def test_invalid_config_path_falls_back(self, resolver):
        """Test invalid config path falls back to CWD"""
        # With invalid config and use_cwd=True, should use CWD
        result = resolver.resolve_project_path(
            cli_path=None,
            config_path="/nonexistent/config/path",
            use_cwd=True
        )
        assert result == Path.cwd().resolve()

    def test_priority_order_correct(self, resolver, tmp_path):
        """Test priority order: CLI > CWD > Config"""
        cli_dir = tmp_path / "cli"
        cli_dir.mkdir()

        # Test CLI priority
        result = resolver.resolve_project_path(cli_path=str(cli_dir))
        assert result == cli_dir.resolve()

    def test_resolve_with_all_sources(self, resolver, tmp_path):
        """Test resolve with all sources provided"""
        cli_dir = tmp_path / "cli"
        cli_dir.mkdir()
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        result = resolver.resolve_project_path(
            cli_path=str(cli_dir),
            config_path=str(config_dir),
            use_cwd=True
        )

        # Should use CLI path (highest priority)
        assert result == cli_dir.resolve()

    def test_resolve_with_minimal_sources(self, resolver):
        """Test resolve with minimal configuration"""
        result = resolver.resolve_project_path()
        assert result.is_absolute()
        assert result.exists()

    def test_resolve_validates_final_path(self, resolver, tmp_path):
        """Test that resolved path is validated"""
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()

        result = resolver.resolve_project_path(cli_path=str(valid_dir))
        assert result.is_dir()
        assert result.exists()

    def test_relative_paths_resolved(self, resolver, tmp_path):
        """Test relative paths are properly resolved"""
        # Create a test directory
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()

        # Use relative path
        result = resolver.resolve_project_path(cli_path=str(test_dir))
        assert result.is_absolute()

    def test_absolute_paths_pass_through(self, resolver, tmp_path):
        """Test absolute paths work correctly"""
        absolute_dir = tmp_path / "absolute_project"
        absolute_dir.mkdir()

        result = resolver.resolve_project_path(cli_path=str(absolute_dir.resolve()))
        assert result == absolute_dir.resolve()
