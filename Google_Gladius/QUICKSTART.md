# Quick Start Guide

Get the Multi-Agent Claude CLI Pipeline running in 5 minutes!

## Prerequisites

1. **Python 3.10+** installed
2. **Claude CLI** installed and configured
   ```bash
   claude --version
   ```
   If not installed, visit: https://docs.anthropic.com/claude/docs/claude-cli

3. **Claude API Key** configured (Claude CLI should already have this)

## Installation

```bash
# Navigate to project directory
cd Google_Gladius

# Install dependencies
pip install -r requirements.txt
```

## Your First Pipeline Run

### Step 1: Run a Sample Ticket

```bash
python scripts/run_pipeline.py PROJ-123
```

This will:
- ✅ Fetch the sample ticket about adding user authentication
- ✅ Run the Planner Agent to create an implementation plan
- ✅ Run the Implementer Agent to generate code changes
- ✅ Run the Reviewer Agent to review the implementation
- ✅ Save all artifacts to `runs/PROJ-123_<timestamp>/`

### Step 2: View the Results

```bash
# List all pipeline runs
python scripts/run_pipeline.py --list
```

### Step 3: Check the Output Artifacts

Navigate to the run directory (shown in the output):
```bash
cd runs/PROJ-123_<timestamp>

# View the plan
cat planner/plan.json

# View the implementation
cat implementer/implementation_v1.json

# View the review
cat reviewer/review_v1.json

# View the patch (ready to apply!)
cat patches/changes_v1.patch
```

## Try Other Tickets

The mock MCP includes several sample tickets:

```bash
# Feature: Add authentication
python scripts/run_pipeline.py PROJ-123

# Bug: Fix memory leak
python scripts/run_pipeline.py PROJ-456

# Improvement: Refactor database
python scripts/run_pipeline.py PROJ-789

# Simple feature: Email validation
python scripts/run_pipeline.py PROJ-001
```

## Customize Your Run

### Use a Different Model

```bash
# Use Opus for higher quality (slower, more expensive)
python scripts/run_pipeline.py PROJ-123 --model opus

# Use Haiku for faster results (faster, less expensive)
python scripts/run_pipeline.py PROJ-123 --model haiku
```

### Adjust Review Iterations

```bash
# Allow up to 3 review/revision cycles
python scripts/run_pipeline.py PROJ-123 --max-iterations 3
```

### Increase Timeout

```bash
# For complex tickets that need more processing time
python scripts/run_pipeline.py PROJ-789 --timeout 600
```

## Understanding the Output

### Console Output

The pipeline prints progress in real-time:
```
============================================================
Starting pipeline for ticket: PROJ-123
============================================================

📁 Run directory: runs/PROJ-123_20241216_143052

🎫 Fetching ticket data...
   Title: Add user authentication to API
   Type: feature

📋 Phase 1: Planning
------------------------------------------------------------
✅ Plan created: 8 steps

💻 Phase 2: Implementation & Review
------------------------------------------------------------

🔄 Iteration 1/2
   → Running implementer...
   ✅ Implementation complete: 4 changes
   → Running reviewer...
   ✅ Review APPROVED

============================================================
✅ Pipeline Complete: SUCCESS
============================================================
Duration: 187.3s
Iterations: 1
Files changed: 4
Issues found: 0
Output: runs/PROJ-123_20241216_143052
```

### Artifact Structure

Each run creates a complete audit trail:

```
runs/PROJ-123_20241216_143052/
├── ticket.json              # Original ticket from MCP
├── summary.json             # Final metrics & status
├── planner/
│   └── plan.json           # Step-by-step implementation plan
├── implementer/
│   └── implementation_v1.json  # Code changes & notes
├── reviewer/
│   └── review_v1.json      # Review feedback & verdict
└── patches/
    └── changes_v1.patch    # Unified diff (git-compatible)
```

### Summary Metrics

The `summary.json` includes:
- **status**: SUCCESS, MAX_ITERATIONS_REACHED, or FAILED
- **approved**: Whether reviewer approved
- **iterations**: Number of review cycles
- **duration_seconds**: Total execution time
- **files_changed**: Count of modified files
- **critical_issues**: Count of critical problems found

## Common Use Cases

### 1. Generate Implementation Plan Only

Run the pipeline and stop after planning:
```bash
python scripts/run_pipeline.py PROJ-123 --max-iterations 0
```
(Note: This will fail the pipeline but generate a plan)

### 2. Batch Processing

Process multiple tickets:
```bash
for ticket in PROJ-123 PROJ-456 PROJ-789; do
    python scripts/run_pipeline.py $ticket
done
```

### 3. Review Historical Runs

```bash
# List all runs
python scripts/run_pipeline.py --list

# Filter by specific ticket
python scripts/run_pipeline.py --list --ticket-id PROJ-123
```

### 4. Clean Up Storage

```bash
# Keep only last 10 runs
python scripts/run_pipeline.py --cleanup 10
```

## Troubleshooting

### "claude: command not found"

Install Claude CLI:
```bash
# Follow installation instructions at:
# https://docs.anthropic.com/claude/docs/claude-cli
```

### "No module named 'pydantic'"

Install dependencies:
```bash
pip install -r requirements.txt
```

### Pipeline Takes Too Long

- Use `--model haiku` for faster responses
- Reduce `--timeout` to fail faster on hanging requests
- Reduce `--max-iterations` to limit review cycles

### Review Keeps Requesting Changes

This is normal! The reviewer agent is thorough. Options:
- Review the issues in `reviewer/review_v1.json`
- Increase `--max-iterations` to allow more revision attempts
- Check if the ticket requirements are clear

## Running Tests

Verify everything works:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only integration tests
pytest tests/test_integration.py -v

# Run only unit tests
pytest tests/test_agents.py -v
```

## Next Steps

1. **Explore the code**: Check out the agent implementations in `src/agents/`
2. **Read the docs**: See [README.md](README.md) for architecture details
3. **Customize agents**: Modify prompts in `prompts/` directory
4. **Add real MCP**: Replace `MockMCPClient` with Jira integration
5. **Configure settings**: Edit `config/settings.yaml` for your environment

## Getting Help

- **Documentation**: [README.md](README.md)
- **Implementation Details**: [PHASE_3_4_COMPLETE.md](PHASE_3_4_COMPLETE.md)
- **Agent Details**: [PHASE_1_2_COMPLETE.md](PHASE_1_2_COMPLETE.md)

## Example Session

Here's a complete example session:

```bash
# 1. Run pipeline
$ python scripts/run_pipeline.py PROJ-123
# ... pipeline executes ...
# ✅ Pipeline Complete: SUCCESS

# 2. List runs
$ python scripts/run_pipeline.py --list
# 📁 PROJ-123_20241216_143052
#    Status: ✅ SUCCESS
#    Duration: 187.3s
#    Iterations: 1
#    Files changed: 4

# 3. View the patch
$ cat runs/PROJ-123_20241216_143052/patches/changes_v1.patch
# --- /dev/null
# +++ b/src/auth/jwt.py
# @@ -0,0 +1,25 @@
# +import jwt
# +from datetime import datetime, timedelta
# ...

# 4. View the review
$ cat runs/PROJ-123_20241216_143052/reviewer/review_v1.json | jq .verdict
# "APPROVE"

# 5. Run another ticket
$ python scripts/run_pipeline.py PROJ-456 --model opus
# ... processing bug fix ...
```

---

**You're ready to go!** 🚀

Run your first pipeline with:
```bash
python scripts/run_pipeline.py PROJ-123
```
