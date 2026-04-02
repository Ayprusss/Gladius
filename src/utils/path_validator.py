"""Path validation utilities for project path handling"""
import os
from pathlib import Path
from typing import Union


class PathValidator:
    """Validate and normalize project paths"""

    @staticmethod
    def validate_project_path(path: Union[str, Path]) -> Path:
        """
        Validate project path

        Checks:
        - Path exists
        - Is a directory (not a file)
        - Is readable
        - Converts to absolute path

        Args:
            path: Project path (absolute or relative)

        Returns:
            Normalized absolute Path object

        Raises:
            ValueError: If path is invalid with descriptive message

        Examples:
            >>> PathValidator.validate_project_path(".")
            PosixPath('/current/working/directory')

            >>> PathValidator.validate_project_path("/path/to/project")
            PosixPath('/path/to/project')
        """
        # Convert to Path object
        if isinstance(path, str):
            path = Path(path)

        # Convert to absolute path
        path = path.resolve()

        # Check exists
        if not path.exists():
            raise ValueError(
                f"Project path does not exist: {path}\n"
                f"Current directory: {Path.cwd()}\n"
                f"Please check the path and try again."
            )

        # Check is directory
        if not path.is_dir():
            raise ValueError(
                f"Project path must be a directory, not a file: {path}\n"
                f"This appears to be a file.\n"
                f"Did you mean the parent directory: {path.parent}?"
            )

        # Check readable
        if not os.access(path, os.R_OK):
            raise ValueError(
                f"Project path is not readable: {path}\n"
                f"Please check file permissions.\n"
                f"Try: chmod +r {path}"
            )

        return path
