# Implementation Plan: Direct User Requests & Auto Path Detection

## Overview

This document outlines the implementation plan to add two major features to the Google_Gladius Multi-Agent Claude CLI Pipeline:

1. **Direct User Requests**: Accept natural language requests instead of requiring JIRA ticket IDs
2. **Automatic Project Path Detection**: Use current working directory as project location automatically

## Goals

- Enable usage: `cd /my/project && gladius "Add login button"`
- Maintain backward compatibility with ticket-based workflow
- Clean architecture that extends existing design
- Production-ready implementation with comprehensive testing

---

## Architecture Design

### Core Design Philosophy
**Unified Request Interface**: Create a flexible system that handles both ticket IDs and natural language requests transparently.

### Request Processing Flow
```
Input String → RequestParser → Detect Type (TICKET | NATURAL)
    ↓
    if TICKET → MCPClient.get_ticket()
    if NATURAL → DirectRequestAdapter.create_synthetic_ticket()
    ↓
Unified Ticket Data → Existing Pipeline (unchanged)
```

### Project Path Resolution (Priority Order)
1. CLI argument `--project-path` (explicit override)
2. Current working directory (automatic - default)
3. Configuration file fallback

---

## New Components

### 1. Request Processing Layer (`src/request_processor/`)

#### `request_parser.py`
```python
class RequestParser:
    """Parse and classify user requests"""

    @staticmethod
    def parse(input_string: str) -> Tuple[RequestType, str]:
        """Determine if input is ticket ID or natural request"""
        # Pattern: PROJ-123, ABC-45, etc.
        # If matches, return TICKET; otherwise NATURAL
```

#### `request_adapter.py`
```python
class DirectRequestAdapter:
    """Convert natural language to synthetic ticket format"""

    def create_synthetic_ticket(self, request: str) -> Dict[str, Any]:
        """
        Creates ticket structure:
        {
            "key": "DIRECT-{timestamp}",
            "title": "{first 50 chars}",
            "description": "{full request}",
            "type": "{auto-detected or 'feature'}",
            "priority": "medium",
            "_is_direct_request": True
        }
        """
```

#### `type_detector.py`
```python
class RequestTypeDetector:
    """Infer ticket type from request keywords"""

    BUG_KEYWORDS = ["fix", "bug", "error", "crash", "leak"]
    FEATURE_KEYWORDS = ["add", "create", "implement", "new"]
    IMPROVEMENT_KEYWORDS = ["refactor", "optimize", "improve"]

    @staticmethod
    def detect_type(request: str) -> str:
        """Return: feature, bug, or improvement"""
```

### 2. Path Resolution Layer (`src/utils/`)

#### `path_resolver.py`
```python
class ProjectPathResolver:
    """Resolve project path from multiple sources"""

    def resolve_project_path(
        self,
        cli_path: Optional[str] = None,
        config_path: Optional[str] = None,
        use_cwd: bool = True
    ) -> Path:
        """
        Priority:
        1. CLI argument (explicit)
        2. Current working directory (auto)
        3. Config file default
        """
```

#### `path_validator.py`
```python
class PathValidator:
    """Validate project paths"""

    @staticmethod
    def validate_project_path(path: Path) -> Path:
        """
        Checks:
        - Exists
        - Is directory
        - Is readable
        - Converts to absolute path
        """
```

### 3. Unified MCP Client (`src/mcp/`)

#### `unified_mcp_client.py`
```python
class UnifiedMCPClient(MCPClient):
    """Handle both ticket IDs and direct requests"""

    def get_ticket(self, request: str) -> Dict[str, Any]:
        """
        1. Try parsing as ticket ID
        2. If ticket ID, fetch from MCP
        3. If natural request, create synthetic ticket
        4. If ticket lookup fails, fallback to synthetic
        """
```

---

## Modifications to Existing Components

### 1. `scripts/run_pipeline.py`

```python
# Change argument
parser.add_argument(
    "request",  # Was: "ticket_id"
    help="Ticket ID (PROJ-123) or natural request ('Add login button')"
)

parser.add_argument(
    "--project-path",
    default=None,  # Auto-detect CWD
    help="Path to project (default: current directory)"
)

# Add path resolution
path_resolver = ProjectPathResolver()
project_path = path_resolver.resolve_project_path(
    cli_path=args.project_path,
    use_cwd=True
)

# Use unified MCP client
unified_mcp = UnifiedMCPClient(
    ticket_mcp_client=MockMCPClient(),
    request_adapter=DirectRequestAdapter()
)

# Pass to orchestrator
orchestrator.run_pipeline(
    request=args.request,
    project_path=project_path
)
```

### 2. `src/orchestrator.py`

```python
def run_pipeline(
    self,
    request: str,  # Changed from ticket_id
    model: str = "sonnet",
    project_path: Optional[Path] = None  # NEW
) -> Dict[str, Any]:

    # Default to CWD if not specified
    if project_path is None:
        project_path = Path.cwd()

    # Validate
    project_path = PathValidator.validate_project_path(project_path)

    # Get ticket (handles both ticket IDs and requests)
    ticket_data = self.mcp_client.get_ticket(request)

    # Add to context for all agents
    context = {
        "project_path": str(project_path),
        "ticket": ticket_data
    }

    # Save in summary
    summary["project_path"] = str(project_path)
```

### 3. All Agent Files

**Files**: `planner_agent.py`, `implementer_agent.py`, `reviewer_agent.py`

```python
def build_user_message(self, context: Dict[str, Any]) -> str:
    ticket = context['ticket']
    project_path = context.get('project_path', '.')

    message = f"""# Project Information
Project Location: {project_path}

# Ticket Details
**ID:** {ticket['key']}
**Title:** {ticket['title']}
...
"""
```

### 4. Prompt Files

Add to each prompt:
```text
PROJECT CONTEXT:
- Project location: {project_path}
- All file references are relative to this root
- This is your working directory

DIRECT REQUEST HANDLING:
- Some tickets are from direct user requests (not JIRA)
- These have minimal metadata
- Make reasonable assumptions and document them
```

### 5. `config/settings.yaml`

```yaml
pipeline:
  default_project_path: "."
  auto_detect_cwd: true
  validate_project_path: true

direct_requests:
  enabled: true
  default_type: "feature"
  default_priority: "medium"
  synthetic_ticket_prefix: "DIRECT"
```

---

## CLI Interface

### New Usage Examples

```bash
# Traditional (unchanged)
python scripts/run_pipeline.py PROJ-123

# Direct request with auto path (CWD)
cd /path/to/project
python scripts/run_pipeline.py "Add login button"

# Direct request with explicit path
python scripts/run_pipeline.py "Fix memory leak" --project-path /my/project

# Complex request
python scripts/run_pipeline.py "Refactor auth to use JWT" --model opus --max-iterations 3

# Still works from anywhere
cd /tmp
python /path/to/gladius/scripts/run_pipeline.py "Add tests" --project-path /my/project
```

### Updated Help Text

```
usage: run_pipeline.py [-h] [--model {sonnet,opus,haiku}]
                      [--project-path PATH] [request]

positional arguments:
  request               Ticket ID (PROJ-123) or natural request
                       ("Add login button")

optional arguments:
  --project-path PATH   Project codebase path (default: current directory)
  --model MODEL         Claude model (default: sonnet)
  --max-iterations N    Max review cycles (default: 2)

Examples:
  # Ticket workflow
  python scripts/run_pipeline.py PROJ-123

  # Direct request (auto-detects current directory)
  cd /my/project && python scripts/run_pipeline.py "Add error handling"

  # Direct request with explicit path
  python scripts/run_pipeline.py "Fix bug" --project-path /my/project
```

---

## Implementation Phases

### Phase 1: Project Path Support (7.5 hours)
**Priority**: Highest - Foundation for both features

1. Create `src/utils/path_validator.py` + tests
2. Create `src/utils/path_resolver.py` + tests
3. Update `config/settings.yaml`
4. Modify `src/orchestrator.py` to accept project_path
5. Update CLI script with `--project-path` argument
6. Update all 3 agents to use project_path in context
7. Test path resolution thoroughly

### Phase 2: Request Processing (7.5 hours)
**Priority**: High - Core feature

8. Create `src/request_processor/request_parser.py` + tests
9. Create `src/request_processor/request_adapter.py` + tests
10. Create `src/request_processor/type_detector.py` + tests
11. Create `src/mcp/unified_mcp_client.py` + tests
12. Update orchestrator to use `request` parameter
13. Integration tests for request processing

### Phase 3: CLI Integration (4 hours)
**Priority**: High - User interface

14. Update CLI argument from `ticket_id` to `request`
15. Update help text and examples
16. Improve error messages
17. Update list/cleanup commands for synthetic tickets
18. End-to-end CLI testing

### Phase 4: Documentation & Polish (6.5 hours)
**Priority**: Medium - Production readiness

19. Update README.md with new usage
20. Update QUICKSTART.md with examples
21. Create DIRECT_REQUESTS.md tutorial
22. Enhanced error handling and messages
23. Comprehensive integration tests
24. Manual testing checklist

### Phase 5: Optional Enhancements (6 hours)
**Priority**: Low - Future nice-to-haves

25. Interactive mode for ambiguous requests
26. Request templates for common patterns
27. Shell script wrapper (`gladius` command)

---

## Testing Strategy

### Unit Tests (~67 tests)

```
tests/unit/
├── test_path_validator.py       (10 tests)
├── test_path_resolver.py        (12 tests)
├── test_request_parser.py       (15 tests)
├── test_request_adapter.py      (10 tests)
├── test_type_detector.py        (8 tests)
└── test_unified_mcp.py          (12 tests)
```

### Integration Tests (~23 tests)

```
tests/integration/
├── test_direct_requests.py      (8 tests)
├── test_project_path.py         (10 tests)
└── test_backward_compat.py      (5 tests)
```

### Manual Testing (20 scenarios)

```bash
# Backward compatibility
python scripts/run_pipeline.py PROJ-123

# Direct request with auto path
cd /project && python gladius/scripts/run_pipeline.py "Add login"

# Direct request with explicit path
python scripts/run_pipeline.py "Fix bug" --project-path /project

# Edge cases
python scripts/run_pipeline.py ""  # Empty
python scripts/run_pipeline.py "PROJ-999"  # Non-existent ticket
--project-path /nonexistent  # Invalid path

# Complex scenarios
cd /project && python gladius/scripts/run_pipeline.py "Refactor auth" --model opus --max-iterations 3
```

---

## Edge Cases Handled

### Input Edge Cases
1. Empty/whitespace request → Error with helpful message
2. Request that looks like ticket but isn't → Try lookup, fallback to natural
3. Very long request (>1000 chars) → Truncate title, full text in description
4. Special characters → Preserve all, document shell escaping
5. Multi-line request → Use first line for title

### Path Edge Cases
6. Non-existent path → Validate and show clear error
7. Path is file not directory → Validate and show error
8. No read permissions → Check and show access error
9. Relative path with spaces → Handle properly, convert to absolute
10. Symlink to directory → Resolve and validate target

### Workflow Edge Cases
11. CWD not a project → Allow, agents work with available files
12. Running from Gladius dir itself → Distinguish working ON vs USING
13. Simultaneous runs → Timestamp IDs ensure uniqueness
14. Valid ticket format but meant as natural → Try lookup, fallback if fails
15. Project path contains 'runs' → No conflict

---

## Time Estimates

| Phase | Time | Description |
|-------|------|-------------|
| Phase 1 | 7.5 hours | Project path support (foundation) |
| Phase 2 | 7.5 hours | Request processing (core feature) |
| Phase 3 | 4 hours | CLI integration (user interface) |
| **Core Implementation** | **19 hours** | Phases 1-3 |
| Phase 4 | 6.5 hours | Documentation & polish |
| **Production Ready** | **25.5 hours** | Phases 1-4 |
| Phase 5 | 6 hours | Optional enhancements |
| **Full Implementation** | **31.5 hours** | All phases |

**Recommendation**: Implement Phases 1-4 for production system (~3-4 days of work)

---

## Success Criteria

### Functional Requirements
- ✅ Accept both ticket IDs and natural language requests
- ✅ Automatically detect current working directory as project path
- ✅ Allow explicit project path override via CLI
- ✅ Maintain 100% backward compatibility
- ✅ Generate valid synthetic tickets for direct requests

### Non-Functional Requirements
- ✅ Request processing adds <100ms overhead
- ✅ Path validation completes instantly
- ✅ Clear error messages for all failure modes
- ✅ Comprehensive test coverage (>90 tests)
- ✅ Complete documentation with examples

### User Experience
- ✅ Simple command: `cd /project && gladius "Add feature"`
- ✅ Works from any directory
- ✅ Helpful error messages
- ✅ Backward compatible (existing scripts unchanged)

---

## Files to Create (11 new files)

1. `src/request_processor/__init__.py`
2. `src/request_processor/request_parser.py`
3. `src/request_processor/request_adapter.py`
4. `src/request_processor/type_detector.py`
5. `src/utils/path_resolver.py`
6. `src/utils/path_validator.py`
7. `src/mcp/unified_mcp_client.py`
8. `tests/unit/test_request_parser.py`
9. `tests/unit/test_path_resolver.py`
10. `tests/integration/test_direct_requests.py`
11. `docs/DIRECT_REQUESTS.md`

## Files to Modify (8 existing files)

1. `scripts/run_pipeline.py` - Add request arg, path resolution
2. `src/orchestrator.py` - Accept request + project_path params
3. `src/agents/planner_agent.py` - Include project_path in context
4. `src/agents/implementer_agent.py` - Include project_path in context
5. `src/agents/reviewer_agent.py` - Include project_path in context
6. `config/settings.yaml` - Add direct request & path settings
7. `README.md` - Update usage examples
8. `QUICKSTART.md` - Add direct request examples

---

## Next Steps

1. **Review this plan** - Confirm approach and scope
2. **Create feature branch** - `git checkout -b feature/direct-requests`
3. **Implement Phase 1** - Project path support (foundation)
4. **Implement Phase 2** - Request processing (core)
5. **Implement Phase 3** - CLI integration
6. **Implement Phase 4** - Documentation & testing
7. **Test thoroughly** - Unit + integration + manual
8. **Merge to main** - After all tests pass

**Ready to begin implementation?**

---

**Status**: 📋 Plan Complete - Ready for Implementation
**Estimated Effort**: 25.5 hours for production-ready system
**Complexity**: Medium (clean extension of existing architecture)
**Risk**: Low (backward compatible, well-tested approach)
