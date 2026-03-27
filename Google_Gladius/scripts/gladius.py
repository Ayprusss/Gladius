#!/usr/bin/env python3
"""
Gladius - Interactive multi-agent pipeline REPL.

Usage:
    gladius                   Start interactive session
    gladius "Add a feature"   Run a single request and exit
"""
import sys
import os
import shutil
import textwrap
from datetime import datetime
from pathlib import Path

# Ensure src/ imports work when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import PipelineOrchestrator
from src.mcp.mock_mcp import MockMCPClient
from src.mcp.unified_mcp_client import UnifiedMCPClient
from src.request_processor.request_adapter import DirectRequestAdapter
from src.utils.artifact_manager import ArtifactManager
from src.utils.path_resolver import ProjectPathResolver
from src.utils.config import ConfigLoader

# ── Colour helpers ────────────────────────────────────────────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_ORANGE = "\033[38;5;208m"
_CYAN   = "\033[36m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_WHITE  = "\033[97m"

def _c(text: str, *codes: str) -> str:
    """Wrap text in ANSI codes (skipped on Windows without VT support)."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return text
    return "".join(codes) + text + _RESET


LOGO = r"""
   ____  __           ___
  / ___|| |    __ _  |   \ _ _ _ _ ___
 | |  _ | |   / _` | | |) | '_| / (_-<
 | |_| ||____| (_| | |___/|_| |_|_/__/
  \____||______\__,_|
"""


def _term_width() -> int:
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def _divider(char: str = "─") -> str:
    return char * _term_width()


def print_banner(
    model: str,
    project_path: Path,
    artifact_manager: ArtifactManager
) -> None:
    """Print the Claude Code-style welcome banner."""
    width = _term_width()

    print()
    print(_c(LOGO.strip(), _ORANGE, _BOLD))
    print(_c(_divider(), _DIM))

    # Two-column layout: left = meta, right = recent activity
    recent = artifact_manager.list_runs()[:4]

    left_lines = [
        _c(f"  Model   ", _DIM) + _c(f"claude-{model}", _WHITE, _BOLD),
        _c(f"  Path    ", _DIM) + _c(str(project_path), _CYAN),
        _c(f"  Version ", _DIM) + _c("1.0.0", _DIM),
    ]

    right_lines = [_c("  Recent runs", _YELLOW, _BOLD)]
    if recent:
        for run_dir in recent:
            try:
                summary = artifact_manager.load_run_summary(run_dir)
                status = "✅" if summary.get("status") == "SUCCESS" else "❌"
                ts = run_dir.name.split("_", 1)[-1].replace("_", " ") if "_" in run_dir.name else "?"
                ticket = summary.get("ticket_id", run_dir.name)
                right_lines.append(f"  {_c(ts, _DIM)}  {status}  {_c(ticket, _WHITE)}")
            except Exception:
                right_lines.append(f"  {_c(run_dir.name, _DIM)}")
    else:
        right_lines.append(_c("  No runs yet", _DIM))

    col = max(width // 2, 30)
    rows = max(len(left_lines), len(right_lines))
    for i in range(rows):
        left  = left_lines[i]  if i < len(left_lines)  else ""
        right = right_lines[i] if i < len(right_lines) else ""
        # Pad left column (strip ANSI for width calc)
        visible_left = _strip_ansi(left)
        pad = max(0, col - len(visible_left))
        print(left + " " * pad + right)

    print(_c(_divider(), _DIM))
    print()
    _print_help_hint()
    print()


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)


def _print_help_hint() -> None:
    print(
        _c("  Tip: ", _DIM)
        + "type your request and press Enter  "
        + _c("/help", _CYAN) + " for commands  "
        + _c("/quit", _CYAN) + " to exit"
    )


def _print_help() -> None:
    print()
    print(_c("  Commands", _YELLOW, _BOLD))
    cmds = [
        ("/help",         "Show this help message"),
        ("/list",         "List recent pipeline runs"),
        ("/model <name>", "Switch model  (sonnet | opus | haiku)"),
        ("/path <dir>",   "Change the active project path"),
        ("/clear",        "Clear the terminal"),
        ("/quit",         "Exit Gladius"),
    ]
    for cmd, desc in cmds:
        print(f"  {_c(cmd, _CYAN):30s}  {_c(desc, _DIM)}")
    print()


def _print_run_list(artifact_manager: ArtifactManager, ticket_id: str = None) -> None:
    runs = artifact_manager.list_runs(ticket_id)
    if not runs:
        print(_c("  No runs found.", _DIM))
        return

    print()
    print(_c(f"  {'Run':45s}  {'Status':18s}  {'Duration':10s}", _YELLOW, _BOLD))
    print(_c("  " + _divider("─"), _DIM))
    for run_dir in runs[:10]:
        try:
            summary = artifact_manager.load_run_summary(run_dir)
            status  = summary.get("status", "UNKNOWN")
            dur     = f"{summary.get('duration_seconds', 0):.1f}s"
            if status == "SUCCESS":
                status_fmt = _c("✅ SUCCESS", _GREEN)
            elif status == "MAX_ITERATIONS_REACHED":
                status_fmt = _c("⚠  MAX ITER", _YELLOW)
            else:
                status_fmt = _c(f"❌ {status}", _RED)
            print(f"  {run_dir.name:45s}  {status_fmt:28s}  {_c(dur, _DIM)}")
        except Exception:
            print(f"  {_c(run_dir.name, _DIM)}")
    print()


def _run_pipeline_interactive(
    request: str,
    orchestrator: PipelineOrchestrator,
    model: str,
    project_path: Path
) -> None:
    """Run the pipeline and print rich phase status."""
    print()
    print(_c(_divider("─"), _DIM))
    try:
        summary = orchestrator.run_pipeline(
            request=request,
            model=model,
            project_path=project_path
        )
        status = summary.get("status", "UNKNOWN")
        if status == "SUCCESS":
            print(_c(f"\n  ✅  Pipeline complete — APPROVED", _GREEN, _BOLD))
        elif status == "MAX_ITERATIONS_REACHED":
            print(_c(f"\n  ⚠   Pipeline complete — max iterations reached", _YELLOW, _BOLD))
        else:
            print(_c(f"\n  ❌  Pipeline failed: {status}", _RED, _BOLD))

        dur   = summary.get("duration_seconds", 0)
        iters = summary.get("iterations", "?")
        files = summary.get("files_changed", 0)
        print(
            _c(f"     {dur:.1f}s", _DIM) + "  "
            + _c(f"{iters} iteration(s)", _DIM) + "  "
            + _c(f"{files} file(s) changed", _DIM)
        )
        run_dir = summary.get("run_directory", "")
        if run_dir:
            print(_c(f"\n  Artifacts → {run_dir}", _DIM))

    except KeyboardInterrupt:
        print(_c("\n  ⚠   Run cancelled.", _YELLOW))
    except Exception as e:
        print(_c(f"\n  ❌  Error: {e}", _RED))
    print()


def _build_orchestrator(
    config: dict,
    project_path: Path,
    args_model: str,
    args_timeout: int,
    args_max_iter: int,
    runs_dir: str
) -> tuple:
    """Create the MCP client + orchestrator from config."""
    mock_mcp       = MockMCPClient()
    request_adapter = DirectRequestAdapter()
    mcp_client     = UnifiedMCPClient(
        ticket_mcp_client=mock_mcp,
        request_adapter=request_adapter
    )
    artifact_manager = ArtifactManager(base_dir=runs_dir)
    orchestrator   = PipelineOrchestrator(
        mcp_client=mcp_client,
        artifact_manager=artifact_manager,
        claude_path=config.get("claude", {}).get("cli_path", "claude"),
        timeout=args_timeout,
        max_review_iterations=args_max_iter
    )
    return orchestrator, artifact_manager


def interactive_loop(
    model: str,
    project_path: Path,
    orchestrator: PipelineOrchestrator,
    artifact_manager: ArtifactManager
) -> None:
    """Main REPL loop."""
    print_banner(model, project_path, artifact_manager)

    while True:
        try:
            raw = input(_c("  > ", _ORANGE, _BOLD)).strip()
        except KeyboardInterrupt:
            print()
            print(_c("  Bye!", _DIM))
            break
        except EOFError:
            break

        if not raw:
            continue

        # ── Slash commands ────────────────────────────────────────────────────
        if raw.startswith("/"):
            parts = raw.split(maxsplit=1)
            cmd   = parts[0].lower()
            arg   = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit", "/q"):
                print(_c("  Bye!", _DIM))
                break

            elif cmd == "/help":
                _print_help()

            elif cmd == "/list":
                _print_run_list(artifact_manager)

            elif cmd == "/clear":
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner(model, project_path, artifact_manager)

            elif cmd == "/model":
                valid = ("sonnet", "opus", "haiku")
                if arg.lower() in valid:
                    model = arg.lower()
                    print(_c(f"  Model switched to {model}", _GREEN))
                else:
                    print(_c(f"  Unknown model. Choose from: {' | '.join(valid)}", _RED))

            elif cmd == "/path":
                new_path = Path(arg).expanduser()
                if new_path.is_dir():
                    project_path = new_path.resolve()
                    print(_c(f"  Project path → {project_path}", _GREEN))
                else:
                    print(_c(f"  Directory not found: {arg}", _RED))

            else:
                print(_c(f"  Unknown command: {cmd}  Try /help", _RED))

            continue

        # ── Pipeline request ──────────────────────────────────────────────────
        _run_pipeline_interactive(raw, orchestrator, model, project_path)


def main() -> None:
    import argparse
    import logging

    parser = argparse.ArgumentParser(
        prog="gladius",
        description="Gladius — interactive multi-agent Claude CLI pipeline",
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Run a single request and exit instead of starting the REPL"
    )
    parser.add_argument("--model", default=None, choices=["sonnet", "opus", "haiku"])
    parser.add_argument("--project-path", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--runs-dir", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging (suppress unless --debug)
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s %(name)s: %(message)s")

    # Load config
    config = ConfigLoader.load_config()
    pipeline_cfg = config.get("pipeline", {})
    claude_cfg   = config.get("claude", {})

    model      = args.model or claude_cfg.get("model", "sonnet")
    timeout    = args.timeout or claude_cfg.get("timeout", 300)
    max_iter   = args.max_iterations or pipeline_cfg.get("max_review_iterations", 2)
    runs_dir   = args.runs_dir or pipeline_cfg.get("runs_directory", "runs")

    # Resolve project path
    path_resolver = ProjectPathResolver()
    try:
        project_path = path_resolver.resolve_project_path(
            cli_path=args.project_path,
            use_cwd=True
        )
    except ValueError as e:
        print(f"Error resolving project path: {e}", file=sys.stderr)
        sys.exit(1)

    # Build the pipeline
    orchestrator, artifact_manager = _build_orchestrator(
        config=config,
        project_path=project_path,
        args_model=model,
        args_timeout=timeout,
        args_max_iter=max_iter,
        runs_dir=runs_dir,
    )

    # Single-shot mode
    if args.request:
        _run_pipeline_interactive(args.request, orchestrator, model, project_path)
        return

    # Interactive REPL
    interactive_loop(model, project_path, orchestrator, artifact_manager)


if __name__ == "__main__":
    main()
