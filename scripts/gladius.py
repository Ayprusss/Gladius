#!/usr/bin/env python3
"""
Gladius — interactive multi-agent AI pipeline terminal.

Type a natural language request and watch three specialized AI agents
plan, implement, and review code changes in real time.

Usage:
    gladius                   Launch interactive terminal
    gladius "Add a feature"   Run once and exit
"""
import sys
import os
import subprocess
import shutil
import re
from pathlib import Path

# Ensure src/ imports work when run as a script or installed package
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from src.orchestrator import PipelineOrchestrator
from src.mcp.mock_mcp import MockMCPClient
from src.mcp.unified_mcp_client import UnifiedMCPClient
from src.request_processor.request_adapter import DirectRequestAdapter
from src.utils.artifact_manager import ArtifactManager
from src.utils.path_resolver import ProjectPathResolver
from src.utils.config import ConfigLoader


# ── Terminal style ─────────────────────────────────────────────────────────────
PROMPT_STYLE = Style.from_dict({
    "prompt":         "#ff8c00 bold",   # orange >
    "prompt.arrow":   "#ff8c00",
    "bottom-toolbar": "bg:#1a1a1a #888888",
})


# ── ANSI helpers (for output, not prompt_toolkit text) ─────────────────────────
def _ansi(*codes: str) -> str:
    return "".join(codes)

R   = "\033[0m"
B   = "\033[1m"
DIM = "\033[2m"
ORG = "\033[38;5;208m"
CYN = "\033[36m"
GRN = "\033[32m"
YLW = "\033[33m"
RED = "\033[31m"
WHT = "\033[97m"


def _strip_ansi(s: str) -> str:
    return re.sub(r'\033\[[0-9;]*m', '', s)


def _tw() -> int:
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def _rule(char: str = "─") -> str:
    return DIM + char * _tw() + R


from src.utils.ascii_art import GLADIUS_LOGOS
import random

# ── Banner ─────────────────────────────────────────────────────────────────────
def print_banner(model: str, project_path: Path, artifact_manager: ArtifactManager) -> None:
    w = _tw()
    print()
    logo = random.choice(GLADIUS_LOGOS)
    for line in logo.splitlines():
        print(ORG + B + line + R)
    print(_rule())

    recent = artifact_manager.list_runs()[:4]
    left_lines = [
        f"  {DIM}Model{R}    {WHT}{B}claude-{model}{R}",
        f"  {DIM}Path{R}     {CYN}{project_path}{R}",
        f"  {DIM}Version{R}  1.0.0",
    ]
    right_hdr = f"  {YLW}{B}Recent runs{R}"
    right_body = []
    if recent:
        for run_dir in recent:
            try:
                s = artifact_manager.load_run_summary(run_dir)
                icon = "✅" if s.get("status") == "SUCCESS" else "❌"
                ts   = "_".join(run_dir.name.split("_")[-2:]) if "_" in run_dir.name else run_dir.name
                tid  = s.get("ticket_id", run_dir.name)
                right_body.append(f"  {icon}  {WHT}{tid}{R}  {DIM}{ts}{R}")
            except Exception:
                right_body.append(f"  {DIM}{run_dir.name}{R}")
    else:
        right_body.append(f"  {DIM}No runs yet{R}")

    right_lines = [right_hdr] + right_body
    col         = max(w // 2, 32)
    rows        = max(len(left_lines), len(right_lines))
    for i in range(rows):
        left  = left_lines[i]  if i < len(left_lines)  else ""
        right = right_lines[i] if i < len(right_lines) else ""
        pad   = max(0, col - len(_strip_ansi(left)))
        print(left + " " * pad + right)

    print(_rule())
    print()
    print(
        f"  {DIM}Describe what you want to build and press {R}"
        f"{CYN}Enter{R}  "
        f"  slash commands: {CYN}/help{R}  {CYN}/quit{R}"
    )
    print()


# ── Help / run list ────────────────────────────────────────────────────────────
def print_help() -> None:
    print()
    print(f"  {YLW}{B}Commands{R}")
    cmds = [
        ("/help",          "Show this message"),
        ("/list",          "Show recent pipeline runs"),
        ("/model <name>",  "Switch model  (sonnet | opus | haiku)"),
        ("/path <dir>",    "Change active project directory"),
        ("/clear",         "Clear the terminal"),
        ("/quit",          "Exit Gladius"),
    ]
    for cmd, desc in cmds:
        print(f"  {CYN}{cmd:<22}{R}  {DIM}{desc}{R}")
    print()


def print_run_list(artifact_manager: ArtifactManager) -> None:
    runs = artifact_manager.list_runs()
    if not runs:
        print(f"  {DIM}No runs yet.{R}")
        return
    print()
    print(f"  {YLW}{B}{'Run directory':<45}  Status{R}")
    print(f"  {DIM}" + "─" * 65 + R)
    for run_dir in runs[:10]:
        try:
            s   = artifact_manager.load_run_summary(run_dir)
            st  = s.get("status", "UNKNOWN")
            dur = f"{s.get('duration_seconds', 0):.1f}s"
            if st == "SUCCESS":
                status_fmt = GRN + "✅ SUCCESS" + R
            elif "MAX" in st:
                status_fmt = YLW + "⚠  MAX ITER" + R
            else:
                status_fmt = RED + f"❌ {st}" + R
            print(f"  {run_dir.name:<45}  {status_fmt}  {DIM}{dur}{R}")
        except Exception:
            print(f"  {DIM}{run_dir.name}{R}")
    print()


# ── Pipeline runner ────────────────────────────────────────────────────────────
def run_pipeline_interactive(
    request: str,
    orchestrator: PipelineOrchestrator,
    model: str,
    project_path: Path
) -> None:
    print()
    print(_rule("─"))
    try:
        summary = orchestrator.run_pipeline(
            request=request, model=model, project_path=project_path
        )
        st = summary.get("status", "UNKNOWN")
        if st == "SUCCESS":
            print(f"\n  {GRN}{B}✅  Approved{R}")
        elif "MAX" in st:
            print(f"\n  {YLW}{B}⚠   Max iterations reached{R}")
        else:
            print(f"\n  {RED}{B}❌  Failed: {st}{R}")

        dur   = summary.get("duration_seconds", 0)
        iters = summary.get("iterations", "?")
        files = summary.get("files_changed", 0)
        print(f"     {DIM}{dur:.1f}s  ·  {iters} iteration(s)  ·  {files} file(s){R}")
        if run_dir := summary.get("run_directory"):
            print(f"\n  {DIM}Artifacts → {run_dir}{R}")

    except KeyboardInterrupt:
        print(f"\n  {YLW}Run cancelled.{R}")
    except Exception as e:
        print(f"\n  {RED}Error: {e}{R}")
    print()


# ── REPL ───────────────────────────────────────────────────────────────────────
def interactive_loop(
    model: str,
    project_path: Path,
    orchestrator: PipelineOrchestrator,
    artifact_manager: ArtifactManager,
) -> None:
    history_dir = Path.home() / ".gladius"
    history_dir.mkdir(exist_ok=True)
    history = FileHistory(str(history_dir / "history.txt"))

    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

    session: PromptSession = PromptSession(
        history=history,
        style=PROMPT_STYLE,
        key_bindings=kb,
        multiline=False,
        bottom_toolbar=lambda: HTML(
            f"  <b>gladius</b>  model=<b>{model}</b>  "
            f"path=<b>{str(project_path)[:40]}</b>  "
            "  <i>/help for commands</i>"
        ),
        refresh_interval=0.5,
    )

    print_banner(model, project_path, artifact_manager)

    while True:
        try:
            raw = session.prompt(HTML("<prompt>  ❯ </prompt>")).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {DIM}Bye!{R}\n")
            break

        if not raw:
            continue

        # ── Slash commands ─────────────────────────────────────────────────────
        if raw.startswith("/"):
            parts = raw.split(maxsplit=1)
            cmd   = parts[0].lower()
            arg   = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit", "/q"):
                print(f"  {DIM}Bye!{R}\n")
                break
            elif cmd == "/help":
                print_help()
            elif cmd == "/list":
                print_run_list(artifact_manager)
            elif cmd == "/clear":
                subprocess.run("cls" if sys.platform == "win32" else "clear", shell=True)
                print_banner(model, project_path, artifact_manager)
            elif cmd == "/model":
                valid = ("sonnet", "opus", "haiku")
                if arg.lower() in valid:
                    model = arg.lower()
                    print(f"  {GRN}Model → {model}{R}\n")
                else:
                    print(f"  {RED}Unknown model. Choose: {' | '.join(valid)}{R}\n")
            elif cmd == "/path":
                p = Path(arg).expanduser()
                if p.is_dir():
                    project_path = p.resolve()
                    print(f"  {GRN}Path → {project_path}{R}\n")
                else:
                    print(f"  {RED}Directory not found: {arg}{R}\n")
            else:
                print(f"  {RED}Unknown command: {cmd}  Try /help{R}\n")
            continue

        # ── Natural language request ───────────────────────────────────────────
        run_pipeline_interactive(raw, orchestrator, model, project_path)


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    import logging

    parser = argparse.ArgumentParser(
        prog="gladius",
        description="Gladius — describe what you want to build, watch it happen.",
    )
    parser.add_argument("request", nargs="?", help="Single request (non-interactive)")
    parser.add_argument("--model", default=None, choices=["sonnet", "opus", "haiku"])
    parser.add_argument("--project-path", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--runs-dir", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s %(name)s: %(message)s")

    config       = ConfigLoader.load_config()
    pipeline_cfg = config.get("pipeline", {})
    claude_cfg   = config.get("claude", {})

    model    = args.model      or claude_cfg.get("model", "sonnet")
    timeout  = args.timeout    or claude_cfg.get("timeout", 300)
    max_iter = args.max_iterations or pipeline_cfg.get("max_review_iterations", 2)
    runs_dir = args.runs_dir   or pipeline_cfg.get("runs_directory", "runs")

    path_resolver = ProjectPathResolver()
    try:
        project_path = path_resolver.resolve_project_path(
            cli_path=args.project_path, use_cwd=True
        )
    except ValueError as e:
        print(f"Error resolving project path: {e}", file=sys.stderr)
        sys.exit(1)

    mcp_client = UnifiedMCPClient(
        ticket_mcp_client=MockMCPClient(),
        request_adapter=DirectRequestAdapter()
    )
    artifact_manager = ArtifactManager(base_dir=runs_dir)
    orchestrator     = PipelineOrchestrator(
        mcp_client=mcp_client,
        artifact_manager=artifact_manager,
        claude_path=claude_cfg.get("cli_path", "claude"),
        timeout=timeout,
        max_review_iterations=max_iter,
    )

    if args.request:
        run_pipeline_interactive(args.request, orchestrator, model, project_path)
    else:
        interactive_loop(model, project_path, orchestrator, artifact_manager)


if __name__ == "__main__":
    main()
