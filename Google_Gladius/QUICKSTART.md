# Quick Start Guide

Get Gladius running in 5 minutes.

## Prerequisites

1. **Python 3.10+** installed
2. **Claude CLI** installed and authenticated
   ```bash
   claude --version
   ```

## Installation

For global usage from any project folder, we recommend `pipx` or standard global `pip` installation:

```bash
cd Google_Gladius
pipx install .
```
*(Alternatively, use `pip install .` or `pip install -e .` based on your python environment).*

This installs dependencies, bundles configuration, and registers the `gladius` command globally.

## Launch the Terminal

```bash
gladius
```

The terminal transforms into an interactive session. You'll see a welcome banner with your current model, project path, and recent run history.

## Type Your Request

At the `❯` prompt, describe what you want to build in plain English:

```
  ❯ Add input validation to the login form
  ❯ Fix the memory leak in the data processing module
  ❯ Refactor the database query layer to use connection pooling
  ❯ Write unit tests for the authentication service
```

Press **Enter** to run. Three AI agents will:
1. 📋 **Plan** — analyze your request and create an implementation plan
2. 💻 **Implement** — generate the code changes
3. 👁️ **Review** — evaluate quality and correctness, iterate if needed

## Slash Commands

| Command | Description |
|---|---|
| `/help` | Show all commands |
| `/list` | Show recent run history |
| `/model <name>` | Switch model (`sonnet` \| `opus` \| `haiku`) |
| `/path <dir>` | Change the active project directory |
| `/clear` | Clear the terminal |
| `/quit` | Exit |

## Single-Shot Mode

Run without the interactive terminal:
```bash
gladius "Add input validation to the login form"
```

## Models

| Model | Best for |
|---|---|
| `sonnet` | Default — fast and capable |
| `opus` | Complex tasks or thorough reviews |
| `haiku` | Fastest, simple tasks |

```bash
gladius --model opus
```

## Output Artifacts

Every run saves a complete audit trail:
```
runs/DIRECT-20260327_100000/
├── ticket.json           # Parsed request
├── planner/plan.json     # Step-by-step plan
├── implementer/
│   └── implementation_v1.json   # Generated code changes
├── reviewer/
│   └── review_v1.json    # Review verdict
├── patches/
│   └── changes_v1.patch  # Git-compatible diff
└── summary.json          # Run metrics
```

View recent runs at any time:
```
  ❯ /list
```

## Debug Mode

```bash
gladius --debug
```

Enables verbose logging showing every step of the agent pipeline.

## Troubleshooting

**`claude: command not found`**
Install Claude CLI from: https://docs.anthropic.com/claude/docs/claude-cli

**`No module named 'prompt_toolkit'`**
```bash
pip install -e .
```

**Pipeline takes too long**
- Use `--model haiku` for speed
- Use `--max-iterations 1` to limit review cycles

---

**You're ready.** Just type `gladius` and describe what you want to build.
