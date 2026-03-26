# Implementation Plan: Multi-Agent Claude CLI Pipeline

## Executive Summary
Build a Python-based orchestrator that coordinates three specialized Claude CLI agents (Planner → Implementer → Reviewer) to process Jira tickets end-to-end. The system will use Atlassian MCP for ticket context and produce structured, auditable JSON outputs.

## Current State Analysis
- **Location:** `c:\Code\hackathon-projects-and-ideas\Google_Gladius\`
- **Existing:** Only `scripts/projectPlan_README.md` documentation
- **Claude CLI:** Available at `c:\Users\ale\.local\bin\claude`
- **Python:** v3.9.13 available
- **MCP Servers:** Not currently configured (will implement mock-first strategy)
- **Test Target:** Mock_Project available in parent directory

## Architecture Decision: Python + Claude CLI Subprocess
**Rationale:**
- Claude CLI has native `--output-format json` and `--json-schema` support
- Python subprocess management ideal for CLI orchestration
- Pydantic provides robust JSON validation and type safety
- Mock-first strategy enables development without live Jira dependency
- Stateless agents via `--no-session-persistence` flag

## Project Structure

```
c:\Code\hackathon-projects-and-ideas\Google_Gladius\
├── src/
│   ├── __init__.py
│   ├── orchestrator.py              # Main pipeline coordinator
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Abstract base class
│   │   ├── planner_agent.py         # Planner implementation
│   │   ├── implementer_agent.py     # Implementer implementation
│   │   └── reviewer_agent.py        # Reviewer implementation
│   ├── claude_client/
│   │   ├── __init__.py
│   │   ├── cli_invoker.py           # Claude CLI subprocess wrapper
│   │   └── output_parser.py         # JSON validation/parsing
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── mcp_client.py            # MCP integration interface
│   │   └── mock_mcp.py              # Mock MCP for testing
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── planner_schema.py        # Pydantic models
│   │   ├── implementer_schema.py
│   │   └── reviewer_schema.py
│   └── utils/
│       ├── __init__.py
│       ├── artifact_manager.py      # Manages runs/ directory
│       ├── retry_handler.py         # Retry logic
│       └── context_manager.py       # Context size management
├── prompts/
│   ├── planner_prompt.txt           # Planner system prompt
│   ├── implementer_prompt.txt       # Implementer system prompt
│   └── reviewer_prompt.txt          # Reviewer system prompt
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   └── fixtures/
│       └── sample_ticket.json
├── scripts/
│   ├── projectPlan_README.md        # Existing documentation
│   ├── IMPLEMENTATION_PLAN.md       # This plan
│   └── run_pipeline.py              # CLI entry point
├── config/
│   └── settings.yaml                # Configuration
├── runs/                            # Generated artifacts (gitignored)
├── requirements.txt
├── setup.py
└── .gitignore
```

## Implementation Phases

### Phase 1: Foundation (Critical)
**Setup infrastructure that everything depends on**

1. **Create project structure** - All directories and `__init__.py` files
2. **Setup `requirements.txt`** and install dependencies:
   ```
   pydantic>=2.0.0
   pyyaml>=6.0
   pytest>=7.0
   jsonschema>=4.0
   ```
3. **Build Claude CLI wrapper** - `src/claude_client/cli_invoker.py`
   - Invoke Claude CLI with `--output-format json` and `--json-schema`
   - Use `--no-session-persistence` for stateless agents
   - Handle subprocess execution and timeouts (300s default)
4. **Define Pydantic schemas** - `src/schemas/`
   - `planner_schema.py`: summary, assumptions, plan, files_to_change, test_plan, risks
   - `implementer_schema.py`: changes, patch, notes, tests_added_or_updated
   - `reviewer_schema.py`: review_summary, issues, suggested_changes, verdict
5. **Mock MCP implementation** - `src/mcp/mock_mcp.py` with sample tickets

### Phase 2: Agent Implementation (Core)
**Build the three specialized agents**

6. **Base Agent class** - `src/agents/base_agent.py`
   - Abstract interface for all agents
   - Common retry logic (3 attempts with exponential backoff)
   - Output persistence to runs/ directory
7. **Planner Agent** - `src/agents/planner_agent.py` + `prompts/planner_prompt.txt`
   - Converts ticket into actionable plan
   - Identifies files to change, test strategy, risks
8. **Implementer Agent** - `src/agents/implementer_agent.py` + `prompts/implementer_prompt.txt`
   - Generates code changes based on plan
   - Produces unified diff patches
9. **Reviewer Agent** - `src/agents/reviewer_agent.py` + `prompts/reviewer_prompt.txt`
   - Reviews implementation for correctness and quality
   - Returns APPROVE or REQUEST_CHANGES verdict

### Phase 3: Orchestration (Pipeline)
**Coordinate agents into working pipeline**

10. **Artifact Manager** - `src/utils/artifact_manager.py`
    - Create timestamped run directories: `runs/YYYY-MM-DD_HHMMSS_TICKET-ID/`
    - Persist JSON outputs for each agent
    - Generate final markdown report
11. **Main Orchestrator** - `src/orchestrator.py`
    - Load configuration from `config/settings.yaml`
    - Execute Planner → Implementer → Reviewer sequence
    - Handle errors and validation between stages
    - Coordinate data flow between agents
12. **CLI Entry Point** - `scripts/run_pipeline.py`
    - Argument parsing: `--ticket-id PROJ-123` or `--ticket-file ticket.json`
    - Progress reporting to console
    - Exit codes based on review verdict

### Phase 4: Testing & Configuration
**Validate and refine**

13. **Configuration** - `config/settings.yaml`
    - Claude CLI settings (model, timeout, retries)
    - MCP configuration (mock vs real)
    - Agent-specific parameters
14. **Unit tests** - Mock Claude CLI responses, test components independently
15. **Integration test** - Full pipeline with Mock_Project as target repository

## Key Technical Decisions

### 1. Claude CLI Invocation Pattern

```python
# Use Claude CLI's native JSON support
subprocess.run([
    'claude', '--print',
    '--output-format', 'json',
    '--json-schema', json.dumps(schema),
    '--no-session-persistence',
    '--system-prompt', system_prompt,
    user_message
], timeout=300)
```

**Why:**
- Native JSON validation via `--json-schema`
- Stateless execution via `--no-session-persistence`
- MCP integration works out of the box
- No API key management needed

### 2. JSON Enforcement Strategy

**Multi-layer approach:**
1. JSON Schema passed via `--json-schema` flag (enforced by Claude CLI)
2. System prompt with clear JSON instructions
3. Pydantic validation for type safety and additional checks
4. Retry logic with feedback if validation fails

### 3. MCP Integration

**Abstraction layer with mock-first:**
- `MCPClient` abstract interface
- `MockMCPClient` for development/testing (returns sample tickets)
- `AtlassianMCPClient` for production (uses real MCP server)
- Configuration-driven switch between mock and real

### 4. Error Handling

**Retry strategy:**
- Max 3 attempts per agent
- Exponential backoff (2s, 4s, 8s)
- Validation feedback incorporated into retry attempts
- Fallback: Extract JSON from markdown code blocks if needed

### 5. Context Management

**Strategic pruning:**
- Planner: Full ticket + minimal code context
- Implementer: Plan summary + targeted code files only
- Reviewer: Plan summary + implementation + diffs
- Token budget per agent: Planner 100k, Implementer 150k, Reviewer 120k

## Critical Files (Priority Order)

### Tier 1 (Must implement first):
1. **`src/claude_client/cli_invoker.py`** - Foundation for all agent communication
2. **`src/schemas/planner_schema.py`** - Template for other schemas
3. **`src/agents/base_agent.py`** - Template for specific agents
4. **`src/mcp/mock_mcp.py`** - Enables testing without Jira

### Tier 2 (Core functionality):
5. **`src/agents/planner_agent.py`** + **`prompts/planner_prompt.txt`**
6. **`src/agents/implementer_agent.py`** + **`prompts/implementer_prompt.txt`**
7. **`src/agents/reviewer_agent.py`** + **`prompts/reviewer_prompt.txt`**
8. **`src/orchestrator.py`** - Ties everything together

### Tier 3 (Polish):
9. **`src/utils/artifact_manager.py`** - Persistence and reporting
10. **`scripts/run_pipeline.py`** - User-facing CLI
11. **`config/settings.yaml`** - Configuration
12. **`tests/`** - Validation

## Expected Artifacts

Each pipeline run generates:
```
runs/2025-12-16_143022_PROJ-123/
├── ticket.json           # Original ticket data
├── planner.json          # Planner output
├── implementer.json      # Implementer output
├── reviewer.json         # Reviewer output
├── final_report.md       # Human-readable summary
└── metadata.json         # Run metadata (timestamps, versions)
```

## Success Criteria

✅ Execute all three agents in sequence successfully
✅ Generate valid JSON outputs conforming to Pydantic schemas
✅ Persist all artifacts in timestamped runs/ directory
✅ Generate readable final markdown report
✅ Handle errors gracefully with retry logic
✅ Demonstrate with example ticket from Mock_Project

## Potential Challenges & Mitigations

### Challenge 1: JSON Wrapped in Markdown
**Mitigation:** Regex extraction as fallback if direct JSON parse fails

### Challenge 2: Context Window Overflow
**Mitigation:** Token budgets per agent, prioritize critical information

### Challenge 3: Schema Validation Failures
**Mitigation:** Partial validation with warnings, retry with feedback

### Challenge 4: MCP Server Unavailable
**Mitigation:** Automatic fallback to MockMCPClient

### Challenge 5: Subprocess Timeouts
**Mitigation:** Configurable timeouts, graceful error handling

## Demo Strategy

**Narrative for hackathon:**
1. Show Jira ticket (or mock ticket JSON)
2. Run: `python scripts/run_pipeline.py --ticket-file tests/fixtures/sample_ticket.json`
3. Show real-time progress through each agent
4. Walk through generated artifacts:
   - `planner.json` - the analysis and plan
   - `implementer.json` - the proposed code changes
   - `reviewer.json` - the quality assessment
   - `final_report.md` - the summary
5. Highlight: Stateless agent coordination, structured outputs, MCP integration

## Estimated Timeline

- **Phase 1 (Foundation):** 3-4 hours
- **Phase 2 (Agents):** 4-5 hours
- **Phase 3 (Orchestration):** 3-4 hours
- **Phase 4 (Testing):** 2-3 hours
- **Total:** 12-16 hours for full MVP

## Next Steps

1. Confirm Claude CLI flags and JSON schema support work as expected
2. Create basic project structure and install dependencies
3. Implement `cli_invoker.py` with simple test
4. Define Pydantic schemas for all three agents
5. Build base agent class with retry logic
6. Implement each agent one at a time with testing
7. Build orchestrator to coordinate the pipeline
8. Create CLI entry point and configuration
9. Test end-to-end with sample ticket
10. Iterate on prompts based on output quality
