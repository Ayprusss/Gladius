"""Path resolution utilities with priority-based resolution"""
from pathlib import Path
from typing import Optional
from .path_validator import PathValidator


class ProjectPathResolver:
    """Resolve project path from multiple sources with priority"""

    def resolve_project_path(
        self,
        cli_path: Optional[str] = None,
        config_path: Optional[str] = None,
        use_cwd: bool = True
    ) -> Path:
        """
        Resolve project path with priority:
        1. CLI argument (explicit override)
        2. Current working directory (auto-detect)
        3. Config file default

        Args:
            cli_path: Path from CLI argument
            config_path: Path from configuration file
            use_cwd: Whether to use current directory as fallback (default: True)

        Returns:
            Validated absolute Path

        Raises:
            ValueError: If no valid path can be determined

        Examples:
            >>> resolver = ProjectPathResolver()
            >>> resolver.resolve_project_path(cli_path="/my/project")
            PosixPath('/my/project')

            >>> resolver.resolve_project_path(use_cwd=True)
            PosixPath('/current/working/directory')
        """
        # Priority 1: CLI argument (explicit override)
        if cli_path is not None:
            return PathValidator.validate_project_path(cli_path)

        # Priority 2: Current working directory (auto-detect)
        if use_cwd:
            cwd = Path.cwd()
            return PathValidator.validate_project_path(cwd)

        # Priority 3: Config file
        if config_path is not None:
            return PathValidator.validate_project_path(config_path)

        # Fallback: current directory
        return PathValidator.validate_project_path(Path.cwd())
