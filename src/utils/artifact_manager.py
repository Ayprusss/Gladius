"""Artifact manager for persisting pipeline outputs"""
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional
import shutil


class ArtifactManager:
    """Manages pipeline output artifacts and run history"""

    def __init__(self, base_dir: str = "runs"):
        """
        Initialize artifact manager

        Args:
            base_dir: Base directory for storing runs (default: "runs")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_dir: Optional[Path] = None

    def create_run(self, ticket_id: str) -> Path:
        """
        Create a new run directory for a ticket

        Args:
            ticket_id: Ticket identifier (e.g., "PROJ-123")

        Returns:
            Path to the run directory
        """
        # Create timestamp-based run directory
        # ⚡ Bolt Optimization: Use microsecond precision (%f) to prevent directory name collisions
        # when multiple runs are created rapidly. This avoids the need for synchronous delays (time.sleep).
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        run_name = f"{ticket_id}_{timestamp}"
        run_dir = self.base_dir / run_name

        # Create subdirectories
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "planner").mkdir(exist_ok=True)
        (run_dir / "implementer").mkdir(exist_ok=True)
        (run_dir / "reviewer").mkdir(exist_ok=True)
        (run_dir / "patches").mkdir(exist_ok=True)

        self.current_run_dir = run_dir
        return run_dir

    def save_ticket_data(self, ticket_data: Dict[str, Any]) -> Path:
        """
        Save original ticket data

        Args:
            ticket_data: Ticket information from MCP

        Returns:
            Path to saved ticket file
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        ticket_path = self.current_run_dir / "ticket.json"
        with open(ticket_path, 'w', encoding='utf-8') as f:
            json.dump(ticket_data, f, indent=2)

        return ticket_path

    def save_planner_output(self, output: Dict[str, Any]) -> Path:
        """
        Save planner agent output

        Args:
            output: Planner output dictionary

        Returns:
            Path to saved planner output
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        output_path = self.current_run_dir / "planner" / "plan.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        return output_path

    def save_implementer_output(
        self,
        output: Dict[str, Any],
        iteration: int = 1
    ) -> Path:
        """
        Save implementer agent output

        Args:
            output: Implementer output dictionary
            iteration: Iteration number (for review/revision cycles)

        Returns:
            Path to saved implementer output
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        output_path = self.current_run_dir / "implementer" / f"implementation_v{iteration}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        # Also save the patch separately for easy access
        if 'patch' in output:
            patch_path = self.current_run_dir / "patches" / f"changes_v{iteration}.patch"
            with open(patch_path, 'w', encoding='utf-8') as f:
                f.write(output['patch'])

        return output_path

    def save_reviewer_output(
        self,
        output: Dict[str, Any],
        iteration: int = 1
    ) -> Path:
        """
        Save reviewer agent output

        Args:
            output: Reviewer output dictionary
            iteration: Iteration number (for review/revision cycles)

        Returns:
            Path to saved reviewer output
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        output_path = self.current_run_dir / "reviewer" / f"review_v{iteration}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        return output_path

    def save_run_summary(self, summary: Dict[str, Any]) -> Path:
        """
        Save overall run summary

        Args:
            summary: Summary dictionary with status, iterations, etc.

        Returns:
            Path to saved summary
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        summary_path = self.current_run_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        return summary_path

    def get_run_dir(self) -> Path:
        """
        Get current run directory

        Returns:
            Path to current run directory

        Raises:
            RuntimeError: If no active run
        """
        if not self.current_run_dir:
            raise RuntimeError("No active run. Call create_run() first.")

        return self.current_run_dir

    def list_runs(self, ticket_id: Optional[str] = None) -> list[Path]:
        """
        List all runs, optionally filtered by ticket ID

        Args:
            ticket_id: Optional ticket ID to filter by

        Returns:
            List of run directories
        """
        if ticket_id:
            pattern = f"{ticket_id}_*"
        else:
            pattern = "*"

        runs = sorted(
            [d for d in self.base_dir.glob(pattern) if d.is_dir()],
            key=lambda p: p.name,
            reverse=True  # Most recent first
        )

        return runs

    def load_run_summary(self, run_dir: Path) -> Dict[str, Any]:
        """
        Load summary from a run directory

        Args:
            run_dir: Path to run directory

        Returns:
            Summary dictionary

        Raises:
            FileNotFoundError: If summary doesn't exist
        """
        summary_path = run_dir / "summary.json"
        with open(summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def cleanup_old_runs(self, keep_last: int = 10) -> int:
        """
        Clean up old runs, keeping only the most recent N

        Args:
            keep_last: Number of runs to keep (default: 10)

        Returns:
            Number of runs deleted
        """
        all_runs = self.list_runs()

        if len(all_runs) <= keep_last:
            return 0

        runs_to_delete = all_runs[keep_last:]
        deleted_count = 0

        for run_dir in runs_to_delete:
            try:
                shutil.rmtree(run_dir)
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {run_dir}: {e}")

        return deleted_count
