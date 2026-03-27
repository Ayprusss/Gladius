# Google Gladius - Multi-Agent Claude CLI Pipeline

A multi-agent workflow system that processes Jira tickets end-to-end using three specialized Claude CLI agents: **Planner → Implementer → Reviewer**.

> Project to display Google Claude challenge - creating a Gemini Workflow using multiple Claude CLI agents to fully plan, design, implement and code review a ticket.

## Overview

This project demonstrates a realistic AI-assisted engineering pipeline where stateless agents coordinate through structured JSON outputs to:
1. **Plan** - Analyze tickets and create implementation plans
2. **Implement** - Generate code changes with patches and tests
3. **Review** - Evaluate quality, security, and correctness

## Key Features

- ✅ **Stateless Agents** - Each agent is a separate Claude CLI invocation
- ✅ **Structured Outputs** - All coordination via validated JSON schemas
- ✅ **MCP Integration** - Fetch Jira tickets via Model Context Protocol
- ✅ **Retry Logic** - Exponential backoff with validation feedback
- ✅ **Mock-First** - Develop and test without live Jira connection
- ✅ **Auditable** - All artifacts persisted in timestamped runs


## Quick Start

**⚡ New to this project?** See [QUICKSTART.md](QUICKSTART.md) for a 5-minute getting started guide!

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Claude CLI is available
claude --version
```

## Architecture

### Agent Pipeline Flow

```
Ticket (from MCP) → Planner Agent → Implementer Agent → Reviewer Agent → Final Report
                         ↓                 ↓                  ↓
                    planner.json    implementer.json    reviewer.json
```

### Agents

#### 1. Planner Agent
- **Input:** Jira ticket with requirements
- **Output:** Implementation plan, files to change, test strategy, risks
- **Model:** Sonnet (default)

#### 2. Implementer Agent
- **Input:** Ticket + Plan
- **Output:** Code changes, unified diff patch, tests, notes
- **Model:** Sonnet (default)

#### 3. Reviewer Agent
- **Input:** Ticket + Plan + Implementation
- **Output:** Review summary, issues (critical/major/minor), verdict
- **Model:** Opus (recommended for thoroughness)

## Directory Structure

```
Google_Gladius/
├── src/
│   ├── agents/          # Agent implementations
│   ├── claude_client/   # Claude CLI wrapper
│   ├── mcp/             # MCP integration
│   ├── schemas/         # Pydantic models
│   └── utils/           # Utilities
├── prompts/             # Agent system prompts
├── tests/               # Test suite
├── scripts/             # Entry points and tools
├── config/              # Configuration
└── runs/                # Generated artifacts
```

## Sample Tickets (Mock MCP)

The mock MCP client includes three realistic sample tickets:

- **PROJ-123**: Add user authentication to API (feature)
- **PROJ-456**: Fix memory leak in data processing (bug)
- **PROJ-789**: Refactor database query layer (improvement)

## Usage

```bash
# Run pipeline on a ticket
python scripts/run_pipeline.py PROJ-123

# Use a different model
python scripts/run_pipeline.py PROJ-123 --model opus

# Customize max iterations
python scripts/run_pipeline.py PROJ-123 --max-iterations 3

# List previous runs
python scripts/run_pipeline.py --list

# Filter runs by ticket
python scripts/run_pipeline.py --list --ticket-id PROJ-123

# Cleanup old runs (keep last 10)
python scripts/run_pipeline.py --cleanup 10
```

## Example Output

After a successful run, artifacts are saved to `runs/<ticket-id>_<timestamp>/`:

```
runs/PROJ-123_20241216_143052/
├── ticket.json                      # Original ticket data
├── planner/
│   └── plan.json                   # Planning output
├── implementer/
│   ├── implementation_v1.json      # First implementation
│   └── implementation_v2.json      # After review feedback (if needed)
├── reviewer/
│   ├── review_v1.json              # First review
│   └── review_v2.json              # Second review (if needed)
├── patches/
│   ├── changes_v1.patch            # Unified diff format
│   └── changes_v2.patch            # Revised changes (if needed)
└── summary.json                     # Run summary & metrics
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_agents.py
```

### Manual Agent Testing

```python
from src.claude_client.cli_invoker import ClaudeClient
from src.agents.planner_agent import PlannerAgent
from src.mcp.mock_mcp import MockMCPClient

# Initialize components
claude = ClaudeClient()
planner = PlannerAgent(claude)
mcp = MockMCPClient()

# Get a sample ticket
ticket = mcp.get_ticket("PROJ-123")

# Execute planner
context = {"ticket": ticket}
plan = planner.execute(context)

print(plan.summary)
for step in plan.plan:
    print(f"- {step}")
```

## Configuration

Configuration will be in `config/settings.yaml`:

```yaml
claude_cli:
  command: "claude"
  timeout: 300
  max_retries: 3

agents:
  planner:
    model: "sonnet"
  implementer:
    model: "sonnet"
  reviewer:
    model: "opus"  # Use best model for reviews

mcp:
  enabled: true
  use_mock: true  # Switch to false for real Jira
```

## Design Decisions

### Why Claude CLI over API?
- MCP integration works out of the box
- No API key management needed
- Native JSON schema support
- Stateless execution via flags

### Why Python?
- Excellent subprocess management
- Pydantic for robust validation
- Rich ecosystem for CLI tools
- Natural choice for orchestration

### Why Mock-First?
- Develop without Jira dependency
- Reproducible tests
- Fast iteration
- Easy demo setup

## Documentation

- [Project Summary](docs/PROJECT_SUMMARY.md) - Detailed project summary and status
- [Debug Guide](docs/DEBUG_GUIDE.md) - Troubleshooting instructions

## Contributing

This is a hackathon/demo project. Key areas for contribution:
- Phase 3: Orchestration implementation
- Phase 4: Testing and configuration
- Real Atlassian MCP integration
- Performance optimizations
- Additional agent types

## License

MIT License

## Acknowledgments

- Anthropic for Claude and Claude CLI
- Google for the Gladius hackathon opportunity
- Atlassian for MCP server integration
