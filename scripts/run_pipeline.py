#!/usr/bin/env python3
"""CLI entry point for running the multi-agent pipeline"""
import argparse
import sys
import io
import logging
from pathlib import Path

# Fix Windows console encoding to support Unicode/emoji
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import PipelineOrchestrator
from src.mcp.mock_mcp import MockMCPClient
from src.mcp.unified_mcp_client import UnifiedMCPClient
from src.request_processor.request_adapter import DirectRequestAdapter
from src.utils.artifact_manager import ArtifactManager
from src.utils.path_resolver import ProjectPathResolver
from src.utils.config import ConfigLoader


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Run the multi-agent Claude CLI pipeline for software development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run pipeline for a ticket using default settings
  python scripts/run_pipeline.py PROJ-123

  # Direct natural language request (auto-detects project path)
  cd /my/project
  python scripts/run_pipeline.py "Add login button to homepage"

  # Direct request with explicit project path
  python scripts/run_pipeline.py "Fix memory leak in auth.py" --project-path /my/project

  # Use a different Claude model
  python scripts/run_pipeline.py PROJ-123 --model opus

  # Specify project path explicitly
  python scripts/run_pipeline.py PROJ-123 --project-path /path/to/project

  # Customize review iterations
  python scripts/run_pipeline.py "Refactor database code" --max-iterations 3

  # List all runs
  python scripts/run_pipeline.py --list

  # List runs for specific ticket
  python scripts/run_pipeline.py --list --ticket-id PROJ-123
        """
    )

    # Load config and parse arguments
    config = ConfigLoader.load_config()
    pipeline_config = config.get('pipeline', {})
    claude_config = config.get('claude', {})

    parser.add_argument(
        "request",
        nargs="?",
        help="Ticket ID (e.g., PROJ-123) or natural language request (e.g., \"Add login button\")"
    )

    parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        default=claude_config.get('model', 'sonnet'),
        help="Claude model to use (default: sonnet or config value)"
    )

    parser.add_argument(
        "--claude-path",
        default=claude_config.get('cli_path', 'claude'),
        help="Path to Claude CLI executable (default: claude or config value)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=claude_config.get('timeout', 300),
        help="Timeout for Claude CLI invocations in seconds"
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=pipeline_config.get('max_review_iterations', 2),
        help="Maximum review/revision cycles"
    )

    parser.add_argument(
        "--runs-dir",
        default=pipeline_config.get('runs_directory', 'runs'),
        help="Directory to store run artifacts"
    )

    parser.add_argument(
        "--project-path",
        type=str,
        default=pipeline_config.get('default_project_path', None),
        help="Path to project codebase (default: auto-detect current directory)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List previous runs"
    )

    parser.add_argument(
        "--ticket-id",
        dest="filter_ticket_id",
        help="Filter runs by ticket ID (use with --list)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="N",
        help="Clean up old runs, keeping only the N most recent"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize artifact manager
    artifact_manager = ArtifactManager(base_dir=args.runs_dir)

    # Handle list command
    if args.list:
        list_runs(artifact_manager, args.filter_ticket_id)
        return 0

    # Handle cleanup command
    if args.cleanup is not None:
        cleanup_runs(artifact_manager, args.cleanup)
        return 0

    # Validate request is provided for pipeline run
    if not args.request:
        parser.error("request is required (unless using --list or --cleanup)")

    # Validate request is not empty
    if not args.request.strip():
        print("❌ Error: Request cannot be empty")
        print("\nExamples:")
        print('  python scripts/run_pipeline.py "Add login button"')
        print('  python scripts/run_pipeline.py PROJ-123')
        return 1

    # Initialize unified MCP client (supports both tickets and direct requests)
    mock_mcp = MockMCPClient()
    request_adapter = DirectRequestAdapter()
    mcp_client = UnifiedMCPClient(
        ticket_mcp_client=mock_mcp,
        request_adapter=request_adapter
    )

    # Resolve project path with priority: CLI arg > CWD > Config default
    path_resolver = ProjectPathResolver()
    try:
        project_path = path_resolver.resolve_project_path(
            cli_path=args.project_path,
            use_cwd=True
        )
    except ValueError as e:
        print(f"❌ Error resolving project path: {e}")
        return 1

    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        mcp_client=mcp_client,
        artifact_manager=artifact_manager,
        claude_path=args.claude_path,
        timeout=args.timeout,
        max_review_iterations=args.max_iterations
    )

    # Run pipeline
    try:
        summary = orchestrator.run_pipeline(
            request=args.request,
            model=args.model,
            project_path=project_path
        )

        # Exit with appropriate code
        if summary["status"] == "SUCCESS":
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def list_runs(artifact_manager: ArtifactManager, ticket_id: str = None):
    """List previous pipeline runs"""
    runs = artifact_manager.list_runs(ticket_id)

    if not runs:
        if ticket_id:
            print(f"No runs found for ticket: {ticket_id}")
        else:
            print("No runs found")
        return

    print(f"\n{'='*80}")
    print(f"Pipeline Runs ({len(runs)} total)")
    if ticket_id:
        print(f"Filtered by: {ticket_id}")
    print(f"{'='*80}\n")

    for run_dir in runs:
        try:
            summary = artifact_manager.load_run_summary(run_dir)

            # Format status with emoji
            status = summary.get("status", "UNKNOWN")
            if status == "SUCCESS":
                status_display = "✅ SUCCESS"
            elif status == "MAX_ITERATIONS_REACHED":
                status_display = "⚠️  MAX_ITERATIONS"
            else:
                status_display = f"❌ {status}"

            print(f"📁 {run_dir.name}")
            print(f"   Status: {status_display}")
            print(f"   Ticket: {summary.get('ticket_id', 'N/A')}")
            print(f"   Duration: {summary.get('duration_seconds', 0):.1f}s")
            print(f"   Iterations: {summary.get('iterations', 'N/A')}")
            print(f"   Files changed: {summary.get('files_changed', 0)}")
            print(f"   Critical issues: {summary.get('critical_issues', 0)}")
            print()

        except Exception as e:
            print(f"📁 {run_dir.name}")
            print(f"   ⚠️  Could not load summary: {e}")
            print()


def cleanup_runs(artifact_manager: ArtifactManager, keep_last: int):
    """Clean up old runs"""
    print(f"\n🧹 Cleaning up old runs (keeping last {keep_last})...")

    deleted = artifact_manager.cleanup_old_runs(keep_last)

    if deleted > 0:
        print(f"✅ Deleted {deleted} old run(s)")
    else:
        print("✅ No runs to delete")


if __name__ == "__main__":
    sys.exit(main())
