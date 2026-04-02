"""Unit tests for PathValidator"""
import pytest
from pathlib import Path
import tempfile
import os

from src.utils.path_validator import PathValidator


class TestPathValidator:
    """Tests for PathValidator class"""

    def test_validate_existing_directory(self, tmp_path):
        """Test validation of existing directory"""
        result = PathValidator.validate_project_path(tmp_path)
        assert result == tmp_path.resolve()
        assert result.is_absolute()

    def test_validate_nonexistent_path_raises_error(self):
        """Test rejection of non-existent path"""
        nonexistent = Path("/nonexistent/path/to/project")
        with pytest.raises(ValueError) as exc_info:
            PathValidator.validate_project_path(nonexistent)
        assert "does not exist" in str(exc_info.value)

    def test_validate_file_not_directory_raises_error(self, tmp_path):
        """Test rejection of file path (not directory)"""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError) as exc_info:
            PathValidator.validate_project_path(test_file)
        assert "must be a directory" in str(exc_info.value)
        assert str(test_file.parent) in str(exc_info.value)

    def test_relative_path_converted_to_absolute(self):
        """Test relative path is converted to absolute"""
        relative_path = Path(".")
        result = PathValidator.validate_project_path(relative_path)
        assert result.is_absolute()
        assert result == Path.cwd().resolve()

    def test_string_path_accepted(self, tmp_path):
        """Test that string paths are accepted and converted"""
        result = PathValidator.validate_project_path(str(tmp_path))
        assert isinstance(result, Path)
        assert result == tmp_path.resolve()

    def test_path_object_accepted(self, tmp_path):
        """Test that Path objects are accepted"""
        result = PathValidator.validate_project_path(tmp_path)
        assert isinstance(result, Path)
        assert result == tmp_path.resolve()

    def test_path_with_spaces(self, tmp_path):
        """Test path with spaces in name"""
        dir_with_spaces = tmp_path / "my project folder"
        dir_with_spaces.mkdir()

        result = PathValidator.validate_project_path(dir_with_spaces)
        assert result == dir_with_spaces.resolve()
        assert "my project folder" in str(result)

    def test_nested_path(self, tmp_path):
        """Test deeply nested path"""
        nested = tmp_path / "a" / "b" / "c" / "d"
        nested.mkdir(parents=True)

        result = PathValidator.validate_project_path(nested)
        assert result == nested.resolve()

    def test_current_directory(self):
        """Test validation of current directory"""
        result = PathValidator.validate_project_path(Path.cwd())
        assert result == Path.cwd().resolve()

    def test_parent_directory(self):
        """Test validation of parent directory"""
        parent = Path.cwd().parent
        result = PathValidator.validate_project_path(parent)
        assert result == parent.resolve()
