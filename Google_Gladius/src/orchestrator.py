"""Main orchestrator for multi-agent pipeline"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .claude_client.cli_invoker import ClaudeClient
from .agents.planner_agent import PlannerAgent
from .agents.implementer_agent import ImplementerAgent
from .agents.reviewer_agent import ReviewerAgent
from .mcp.mcp_client import MCPClient
from .utils.artifact_manager import ArtifactManager
from .utils.path_validator import PathValidator


class PipelineOrchestrator:
    """Orchestrates the multi-agent pipeline"""

    def __init__(
        self,
        mcp_client: MCPClient,
        artifact_manager: Optional[ArtifactManager] = None,
        claude_path: str = "claude",
        timeout: int = 300,
        max_review_iterations: int = 2
    ):
        """
        Initialize pipeline orchestrator

        Args:
            mcp_client: MCP client for ticket retrieval
            artifact_manager: Artifact manager for output persistence
            claude_path: Path to Claude CLI executable
            timeout: Timeout for Claude CLI invocations
            max_review_iterations: Maximum review/revision cycles
        """
        self.mcp_client = mcp_client
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.max_review_iterations = max_review_iterations

        # Initialize Claude client
        self.claude_client = ClaudeClient(claude_path=claude_path, timeout=timeout)

        # Initialize agents
        self.planner = PlannerAgent(self.claude_client)
        self.implementer = ImplementerAgent(self.claude_client)
        self.reviewer = ReviewerAgent(self.claude_client)

    def run_pipeline(
        self,
        request: str,
        model: str = "sonnet",
        project_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the full pipeline for a request

        Args:
            request: Ticket ID (e.g., "PROJ-123") or natural language request
                    (e.g., "Add login button")
            model: Claude model to use (sonnet, opus, haiku)
            project_path: Path to project codebase (defaults to current directory)

        Returns:
            Pipeline summary with status and artifacts
        """
        # Resolve and validate project path
        if project_path is None:
            project_path = Path.cwd()
        project_path = PathValidator.validate_project_path(project_path)

        print(f"\n{'='*60}")
        print(f"Starting pipeline for request: {request}")
        print(f"Project location: {project_path}")
        print(f"{'='*60}\n")

        start_time = datetime.now()

        # Fetch ticket data (handles both ticket IDs and natural requests)
        print("🎫 Processing request...")
        ticket_data = self.mcp_client.get_ticket(request)
        ticket_id = ticket_data["key"]

        # Create run directory
        run_dir = self.artifact_manager.create_run(ticket_id)
        print(f"📁 Run directory: {run_dir}\n")

        # Save ticket data
        self.artifact_manager.save_ticket_data(ticket_data)
        print(f"   Ticket ID: {ticket_id}")
        print(f"   Title: {ticket_data.get('title', 'N/A')}")
        print(f"   Type: {ticket_data.get('type', 'N/A')}")

        # Show if this is a direct request
        if ticket_data.get('_is_direct_request'):
            print(f"   Source: Direct request (natural language)")
        else:
            print(f"   Source: Ticket system")
        print()

        # Phase 1: Planning
        print("📋 Phase 1: Planning")
        print("-" * 60)
        plan_output = self._run_planner(ticket_data, model, project_path)
        self.artifact_manager.save_planner_output(plan_output.model_dump())
        print(f"✅ Plan created: {len(plan_output.plan)} steps")
        print(f"\n   Summary: {plan_output.summary}")
        print("   Steps:")
        for i, step in enumerate(plan_output.plan, 1):
            print(f"     {i}. {step}")
        if plan_output.files_to_change:
            print("\n   Files to modify:")
            for file_mod in plan_output.files_to_change:
                print(f"     - {file_mod.path}: {file_mod.reason}")
        print()

        # Phase 2: Implementation with review cycles
        print("💻 Phase 2: Implementation & Review")
        print("-" * 60)

        implementation_approved = False
        iteration = 1
        review_output = None

        while iteration <= self.max_review_iterations and not implementation_approved:
            print(f"\n🔄 Iteration {iteration}/{self.max_review_iterations}")

            # Run implementer
            print("   → Running implementer...")
            impl_output = self._run_implementer(
                ticket_data,
                plan_output,
                review_output,
                iteration,
                model,
                project_path
            )
            self.artifact_manager.save_implementer_output(
                impl_output.model_dump(),
                iteration
            )
            print(f"   ✅ Implementation complete: {len(impl_output.changes)} changes")

            # Run reviewer
            print("   → Running reviewer...")
            review_output = self._run_reviewer(
                ticket_data,
                plan_output,
                impl_output,
                model,
                project_path
            )
            self.artifact_manager.save_reviewer_output(
                review_output.model_dump(),
                iteration
            )

            # Check verdict
            if review_output.verdict == "APPROVE":
                implementation_approved = True
                print(f"   ✅ Review APPROVED")
            else:
                print(f"   ⚠️  Review requested changes:")
                for issue in review_output.issues:
                    if issue.severity in ["critical", "major"]:
                        print(f"      [{issue.severity.upper()}] {issue.description}")

            iteration += 1

        # Determine final status
        if implementation_approved:
            final_status = "SUCCESS"
            status_emoji = "✅"
        elif iteration > self.max_review_iterations:
            final_status = "MAX_ITERATIONS_REACHED"
            status_emoji = "⚠️"
        else:
            final_status = "FAILED"
            status_emoji = "❌"

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create summary
        summary = {
            "ticket_id": ticket_id,
            "status": final_status,
            "approved": implementation_approved,
            "iterations": iteration - 1,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "run_directory": str(run_dir),
            "project_path": str(project_path),
            "request_type": ticket_data.get("_request_type", "ticket"),
            "is_direct_request": ticket_data.get("_is_direct_request", False),
            "plan_summary": plan_output.summary,
            "files_changed": len(impl_output.changes) if impl_output else 0,
            "final_verdict": review_output.verdict if review_output else None,
            "critical_issues": len([
                i for i in review_output.issues
                if i.severity == "critical"
            ]) if review_output else 0
        }

        self.artifact_manager.save_run_summary(summary)

        # Print final summary
        print(f"\n{'='*60}")
        print(f"{status_emoji} Pipeline Complete: {final_status}")
        print(f"{'='*60}")
        print(f"Duration: {duration:.1f}s")
        print(f"Iterations: {iteration - 1}")
        print(f"Files changed: {summary['files_changed']}")
        if review_output:
            print(f"Issues found: {len(review_output.issues)}")
        print(f"Output: {run_dir}\n")

        return summary

    def _run_planner(
        self,
        ticket_data: Dict[str, Any],
        model: str,
        project_path: Path
    ):
        """Run planner agent"""
        context = {
            "ticket": ticket_data,
            "model": model,
            "project_path": str(project_path),
            "project_path_absolute": str(project_path.absolute())
        }
        return self.planner.execute(context)

    def _run_implementer(
        self,
        ticket_data: Dict[str, Any],
        plan_output,
        review_output,
        iteration: int,
        model: str,
        project_path: Path
    ):
        """Run implementer agent"""
        context = {
            "ticket": ticket_data,
            "plan": plan_output,
            "model": model,
            "iteration": iteration,
            "project_path": str(project_path),
            "project_path_absolute": str(project_path.absolute())
        }

        # Include review feedback if this is a revision
        if review_output:
            context["review_feedback"] = {
                "verdict": review_output.verdict,
                "issues": [issue.model_dump() for issue in review_output.issues],
                "suggested_changes": review_output.suggested_changes
            }

        return self.implementer.execute(context)

    def _run_reviewer(
        self,
        ticket_data: Dict[str, Any],
        plan_output,
        impl_output,
        model: str,
        project_path: Path
    ):
        """Run reviewer agent"""
        context = {
            "ticket": ticket_data,
            "plan": plan_output,
            "implementation": impl_output,
            "model": model,
            "project_path": str(project_path),
            "project_path_absolute": str(project_path.absolute())
        }
        return self.reviewer.execute(context)

    def list_runs(self, ticket_id: Optional[str] = None):
        """
        List pipeline runs

        Args:
            ticket_id: Optional ticket ID to filter by

        Returns:
            List of run directories
        """
        return self.artifact_manager.list_runs(ticket_id)

    def get_run_summary(self, run_dir: Path) -> Dict[str, Any]:
        """
        Get summary for a specific run

        Args:
            run_dir: Path to run directory

        Returns:
            Run summary dictionary
        """
        return self.artifact_manager.load_run_summary(run_dir)
