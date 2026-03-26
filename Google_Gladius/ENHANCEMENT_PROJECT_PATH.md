# Enhancement Plan: Project Path Support & Direct User Requests

## Overview

This document outlines the implementation plan to add two critical features to the Google_Gladius Multi-Agent Claude CLI Pipeline:

1. **Project Path Support**: Specify target project directory for the pipeline to analyze and modify
2. **Direct User Requests**: Accept natural language requests instead of requiring JIRA ticket IDs

These features transform the pipeline from a demo system into a production-ready tool that can be used with real projects via simple terminal commands.

---

## Current Limitations

### Problem 1: No Project Path Support
**Issue**: The pipeline has no way to specify which codebase to work on. It implicitly assumes the project is within or relative to the Google_Gladius directory.

**Impact**:
- Cannot work with real projects in different directories
- Agents have no context about where to find existing code
- Generated patches reference non-existent file paths
- Blocks real-world usage beyond demos

### Problem 2: Requires JIRA Tickets
**Issue**: Users must create formal tickets (or use mock tickets) to use the pipeline. Cannot accept simple string requests.

**Impact**:
- Overhead of creating tickets for quick tasks
- Cannot use for ad-hoc development requests
- Not intuitive for solo developers or small teams
- Limits accessibility

---

## Proposed Solution

### Feature 1: Automatic Project Path Detection
Enable the pipeline to automatically use the current working directory as the project path, with optional explicit override.

```bash
# Auto-detect: Use current directory
cd /my/webapp
python /path/to/gladius/scripts/run_pipeline.py PROJ-123

# Explicit: Specify path
python scripts/run_pipeline.py PROJ-123 --project-path /my/webapp
```

### Feature 2: Direct Natural Language Requests
Accept simple string requests that get converted into synthetic tickets automatically.

```bash
# Natural language request
cd /my/project
python gladius/scripts/run_pipeline.py "Add login button to homepage"

# Works with all existing flags
python gladius/scripts/run_pipeline.py "Fix memory leak in auth.py" --model opus
```

### Combined Usage
```bash
# Ultimate simplicity: cd to project, describe what you want
cd /my/webapp
python /path/to/gladius/scripts/run_pipeline.py "Add email validation to signup form"
```

---

## Architecture Design

### Core Design Philosophy
**Unified Request Interface**: Create a flexible system that handles both ticket IDs and natural language requests transparently, with automatic project path detection.

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
1. **CLI argument** `--project-path` (explicit override)
2. **Current working directory** (automatic detection - default)
3. **Configuration file** fallback

### Backward Compatibility
- Existing `PROJ-123` usage works unchanged
- Default project path is current directory (same as before if run from project)
- All existing tests pass without modification
- Zero breaking changes

---

## New Components to Create

### 1. Request Processing Layer (`src/request_processor/`)

#### `__init__.py`
Module initialization for request processing components.

#### `request_parser.py`
```python
from enum import Enum
from typing import Tuple

class RequestType(Enum):
    TICKET = "ticket"
    NATURAL = "natural"

class RequestParser:
    """Parse and classify user requests"""

    # Ticket ID pattern: PROJ-123, ABC-45, etc.
    TICKET_PATTERN = r'^[A-Z]+-\d+$'

    @staticmethod
    def parse(input_string: str) -> Tuple[RequestType, str]:
        """
        Determine if input is ticket ID or natural request

        Args:
            input_string: User input (ticket ID or natural request)

        Returns:
            Tuple of (RequestType, cleaned_input)

        Examples:
            "PROJ-123" → (RequestType.TICKET, "PROJ-123")
            "Add login button" → (RequestType.NATURAL, "Add login button")
        """
        cleaned = input_string.strip()

        if re.match(RequestParser.TICKET_PATTERN, cleaned):
            return (RequestType.TICKET, cleaned)
        else:
            return (RequestType.NATURAL, cleaned)
```

#### `request_adapter.py`
```python
from datetime import datetime
from typing import Dict, Any
from .type_detector import RequestTypeDetector

class DirectRequestAdapter:
    """Convert natural language requests to synthetic ticket format"""

    def __init__(self, ticket_prefix: str = "DIRECT"):
        self.ticket_prefix = ticket_prefix
        self.type_detector = RequestTypeDetector()

    def create_synthetic_ticket(
        self,
        request: str,
        ticket_type: str = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Create synthetic ticket from natural request

        Args:
            request: Natural language request
            ticket_type: Override auto-detection (feature, bug, improvement)
            priority: Ticket priority (default: medium)

        Returns:
            Synthetic ticket in standard format

        Example:
            Input: "Add login button to homepage"
            Output: {
                "key": "DIRECT-20241217143052",
                "title": "Add login button to homepage",
                "description": "Add login button to homepage",
                "type": "feature",
                "priority": "medium",
                "_is_direct_request": True
            }
        """
        # Generate unique ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ticket_id = f"{self.ticket_prefix}-{timestamp}"

        # Auto-detect type if not specified
        if ticket_type is None:
            ticket_type = self.type_detector.detect_type(request)

        # Extract title (first 100 chars or first sentence)
        title = self._extract_title(request)

        return {
            "key": ticket_id,
            "title": title,
            "description": request,  # Full request in description
            "type": ticket_type,
            "priority": priority,
            "status": "open",
            "acceptance_criteria": [],
            "comments": [],
            "related_tickets": [],
            "_is_direct_request": True,  # Flag for agents
            "_request_type": "natural"  # For tracking
        }

    def _extract_title(self, request: str, max_length: int = 100) -> str:
        """Extract title from request (first sentence or truncate)"""
        # Try to get first sentence
        sentences = request.split('.')
        if sentences and len(sentences[0]) <= max_length:
            return sentences[0].strip()

        # Otherwise truncate
        if len(request) <= max_length:
            return request
        else:
            return request[:max_length].rsplit(' ', 1)[0] + "..."
```

#### `type_detector.py`
```python
class RequestTypeDetector:
    """Detect ticket type from request text using keyword analysis"""

    # Keyword mappings
    BUG_KEYWORDS = [
        "fix", "bug", "error", "crash", "leak", "broken",
        "issue", "problem", "failing", "not working"
    ]

    FEATURE_KEYWORDS = [
        "add", "create", "implement", "new", "build",
        "develop", "introduce", "enable"
    ]

    IMPROVEMENT_KEYWORDS = [
        "refactor", "optimize", "improve", "enhance",
        "update", "upgrade", "modernize", "clean"
    ]

    @staticmethod
    def detect_type(request: str) -> str:
        """
        Detect ticket type from request keywords

        Args:
            request: Natural language request

        Returns:
            "bug", "feature", or "improvement"

        Examples:
            "Fix the login bug" → "bug"
            "Add email validation" → "feature"
            "Refactor authentication code" → "improvement"
        """
        request_lower = request.lower()

        # Count keyword matches
        bug_score = sum(1 for kw in RequestTypeDetector.BUG_KEYWORDS
                       if kw in request_lower)
        feature_score = sum(1 for kw in RequestTypeDetector.FEATURE_KEYWORDS
                           if kw in request_lower)
        improvement_score = sum(1 for kw in RequestTypeDetector.IMPROVEMENT_KEYWORDS
                               if kw in request_lower)

        # Return type with highest score
        scores = {
            "bug": bug_score,
            "feature": feature_score,
            "improvement": improvement_score
        }

        max_type = max(scores, key=scores.get)

        # Default to "feature" if no clear match
        if scores[max_type] == 0:
            return "feature"

        return max_type
```

### 2. Path Resolution Layer (`src/utils/`)

#### `path_validator.py`
```python
from pathlib import Path
from typing import Union

class PathValidator:
    """Validate and normalize project paths"""

    @staticmethod
    def validate_project_path(path: Union[str, Path]) -> Path:
        """
        Validate project path

        Checks:
        - Path exists
        - Is a directory (not a file)
        - Is readable
        - Converts to absolute path

        Args:
            path: Project path (absolute or relative)

        Returns:
            Normalized absolute Path object

        Raises:
            ValueError: If path is invalid with descriptive message
        """
        # Convert to Path object
        if isinstance(path, str):
            path = Path(path)

        # Convert to absolute path
        path = path.resolve()

        # Check exists
        if not path.exists():
            raise ValueError(
                f"Project path does not exist: {path}\n"
                f"Please check the path and try again."
            )

        # Check is directory
        if not path.is_dir():
            raise ValueError(
                f"Project path must be a directory, not a file: {path}\n"
                f"Did you mean: {path.parent}?"
            )

        # Check readable
        if not os.access(path, os.R_OK):
            raise ValueError(
                f"Project path is not readable: {path}\n"
                f"Please check permissions."
            )

        return path
```

#### `path_resolver.py`
```python
from pathlib import Path
from typing import Optional
from .path_validator import PathValidator

class ProjectPathResolver:
    """Resolve project path from multiple sources with priority"""

    def resolve_project_path(
        self,
        cli_path: Optional[str] = None,
        config_path: Optional[str] = None,
        use_cwd: bool = True
    ) -> Path:
        """
        Resolve project path with priority:
        1. CLI argument (explicit override)
        2. Current working directory (auto-detect)
        3. Config file default

        Args:
            cli_path: Path from CLI argument
            config_path: Path from configuration file
            use_cwd: Whether to use current directory as fallback

        Returns:
            Validated absolute Path

        Raises:
            ValueError: If no valid path can be determined
        """
        # Priority 1: CLI argument
        if cli_path is not None:
            return PathValidator.validate_project_path(cli_path)

        # Priority 2: Current working directory
        if use_cwd:
            cwd = Path.cwd()
            return PathValidator.validate_project_path(cwd)

        # Priority 3: Config file
        if config_path is not None:
            return PathValidator.validate_project_path(config_path)

        # Fallback: current directory
        return PathValidator.validate_project_path(Path.cwd())
```

### 3. Unified MCP Client (`src/mcp/`)

#### `unified_mcp_client.py`
```python
from typing import Dict, Any
from .mcp_client import MCPClient
from ..request_processor.request_parser import RequestParser, RequestType
from ..request_processor.request_adapter import DirectRequestAdapter

class UnifiedMCPClient(MCPClient):
    """MCP client supporting both ticket IDs and direct requests"""

    def __init__(
        self,
        ticket_mcp_client: MCPClient,
        request_adapter: Optional[DirectRequestAdapter] = None
    ):
        """
        Initialize unified MCP client

        Args:
            ticket_mcp_client: MCP client for fetching actual tickets
            request_adapter: Adapter for creating synthetic tickets
        """
        self.ticket_mcp = ticket_mcp_client
        self.adapter = request_adapter or DirectRequestAdapter()
        self.parser = RequestParser()

    def get_ticket(self, request: str) -> Dict[str, Any]:
        """
        Handle both ticket IDs and natural requests

        Logic:
        1. Parse input to determine type (TICKET or NATURAL)
        2. If TICKET, try to fetch from ticket_mcp
        3. If fetch fails, fallback to synthetic ticket with warning
        4. If NATURAL, create synthetic ticket directly

        Args:
            request: Ticket ID or natural language request

        Returns:
            Ticket data dictionary
        """
        # Parse request type
        request_type, cleaned_request = self.parser.parse(request)

        if request_type == RequestType.TICKET:
            # Try to fetch actual ticket
            try:
                ticket = self.ticket_mcp.get_ticket(cleaned_request)
                ticket["_request_type"] = "ticket"
                return ticket
            except (ValueError, ConnectionError) as e:
                # Ticket not found - treat as natural request
                print(f"Warning: Ticket '{cleaned_request}' not found. "
                      f"Treating as natural request.")
                return self.adapter.create_synthetic_ticket(cleaned_request)

        else:  # NATURAL request
            # Create synthetic ticket
            return self.adapter.create_synthetic_ticket(cleaned_request)

    def health_check(self) -> bool:
        """Delegate to underlying ticket MCP"""
        return self.ticket_mcp.health_check()
```

---

## Modifications to Existing Components

### 1. `scripts/run_pipeline.py`

```python
# Update imports
from src.request_processor.request_adapter import DirectRequestAdapter
from src.mcp.unified_mcp_client import UnifiedMCPClient
from src.utils.path_resolver import ProjectPathResolver

# Change argument name
parser.add_argument(
    "request",  # Changed from "ticket_id"
    nargs="?",
    help="Ticket ID (e.g., PROJ-123) or natural request (e.g., 'Add login button')"
)

# Add project path argument
parser.add_argument(
    "--project-path",
    default=None,
    help="Path to project codebase (default: current directory)"
)

# Resolve project path
path_resolver = ProjectPathResolver()
project_path = path_resolver.resolve_project_path(
    cli_path=args.project_path,
    use_cwd=True
)

# Use unified MCP client
adapter = DirectRequestAdapter()
unified_mcp = UnifiedMCPClient(
    ticket_mcp_client=MockMCPClient(),  # Or JiraMCPClient in production
    request_adapter=adapter
)

# Update orchestrator call
summary = orchestrator.run_pipeline(
    request=args.request,  # Changed from ticket_id
    model=args.model,
    project_path=project_path
)
```

### 2. `src/orchestrator.py`

```python
from pathlib import Path
from typing import Optional
from src.utils.path_validator import PathValidator

def run_pipeline(
    self,
    request: str,  # Changed from ticket_id
    model: str = "sonnet",
    project_path: Optional[Path] = None  # NEW
) -> Dict[str, Any]:
    """Run the full pipeline for a request"""

    # Resolve project path if not provided
    if project_path is None:
        project_path = Path.cwd()

    # Validate project path
    project_path = PathValidator.validate_project_path(project_path)

    print(f"\n{'='*60}")
    print(f"Starting pipeline for request: {request}")
    print(f"Project location: {project_path}")
    print(f"{'='*60}\n")

    # Create run directory
    # Note: For direct requests, ticket_id comes from synthetic ticket
    ticket_data = self.mcp_client.get_ticket(request)
    ticket_id = ticket_data["key"]

    run_dir = self.artifact_manager.create_run(ticket_id)
    print(f"📁 Run directory: {run_dir}\n")

    # Save ticket data
    self.artifact_manager.save_ticket_data(ticket_data)

    # Add project_path to context for all agents
    base_context = {
        "project_path": str(project_path),
        "project_path_absolute": str(project_path.absolute())
    }

    # Phase 1: Planning
    plan_output = self._run_planner(ticket_data, model, base_context)

    # Phase 2: Implementation & Review (existing logic)
    # ...

    # Save project_path in summary
    summary["project_path"] = str(project_path)
    summary["request_type"] = ticket_data.get("_request_type", "ticket")
    summary["is_direct_request"] = ticket_data.get("_is_direct_request", False)
```

### 3. Agent Files (All Three)

**Files**: `planner_agent.py`, `implementer_agent.py`, `reviewer_agent.py`

```python
def build_user_message(self, context: Dict[str, Any]) -> str:
    ticket = context['ticket']
    project_path = context.get('project_path', '.')

    message = f"""# Project Information
Project Location: {project_path}
All file paths should be relative to this project root.

# Ticket Details
**Ticket ID:** {ticket['key']}
**Title:** {ticket['title']}
**Type:** {ticket['type']}
**Description:**
{ticket['description']}
"""

    # Add note for direct requests
    if ticket.get('_is_direct_request'):
        message += """
**Note:** This is a direct user request (not from JIRA).
- Make reasonable assumptions about requirements
- Document your assumptions clearly in the assumptions field
- The user can provide clarification in future iterations if needed
"""

    return message
```

### 4. Prompt Files

**Files**: `planner_prompt.txt`, `implementer_prompt.txt`, `reviewer_prompt.txt`

Add to each prompt:

```text
## PROJECT CONTEXT

You will be provided with a project_path indicating the codebase location.

Important guidelines:
- All file references must be relative to this project root
- Example: If project is at /home/user/myapp, reference files as src/auth.py (not /home/user/myapp/src/auth.py)
- This is your working directory for all operations
- Generated patches will be applied from this root directory

## DIRECT REQUEST HANDLING

Some tickets come from direct user requests rather than formal JIRA tickets.
These tickets have minimal metadata and are marked with _is_direct_request: true.

When handling direct requests:
- Make reasonable assumptions about implementation details
- Document all assumptions clearly in your assumptions field
- Be conservative - prefer simpler solutions when requirements are ambiguous
- Ask for clarification through the assumptions field if critical decisions are unclear
- Remember the user can provide feedback in review cycles
```

### 5. `config/settings.yaml`

```yaml
pipeline:
  # Maximum review/revision cycles
  max_review_iterations: 2

  # Runs directory location
  runs_directory: "runs"

  # Default project path if not specified via CLI
  default_project_path: "."

  # Auto-detect current working directory
  auto_detect_cwd: true

  # Validate project path accessibility
  validate_project_path: true

  # Run retention policy
  keep_last_runs: 10

# Direct request settings
direct_requests:
  # Enable direct natural language requests
  enabled: true

  # Default type for ambiguous requests
  default_type: "feature"

  # Default priority for direct requests
  default_priority: "medium"

  # Prefix for synthetic ticket IDs
  synthetic_ticket_prefix: "DIRECT"

  # Keywords for type detection
  bug_keywords:
    - "fix"
    - "bug"
    - "error"
    - "crash"
    - "leak"
    - "broken"

  feature_keywords:
    - "add"
    - "create"
    - "implement"
    - "new"
    - "build"

  improvement_keywords:
    - "refactor"
    - "optimize"
    - "improve"
    - "enhance"
    - "update"
```

---

## CLI Interface Design

### Updated Help Text

```
usage: run_pipeline.py [-h] [--model {sonnet,opus,haiku}]
                      [--project-path PATH] [--max-iterations N]
                      [--timeout TIMEOUT] [--list] [--cleanup N]
                      [request]

Run the multi-agent Claude CLI pipeline for software development

positional arguments:
  request               Ticket ID (e.g., PROJ-123) or natural request
                       (e.g., "Add login button"). If not provided, use
                       --list or --cleanup commands.

optional arguments:
  -h, --help           show this help message and exit
  --project-path PATH  Path to project codebase (default: current directory)
  --model MODEL        Claude model: sonnet, opus, haiku (default: sonnet)
  --max-iterations N   Maximum review cycles (default: 2)
  --timeout TIMEOUT    Timeout per invocation in seconds (default: 300)
  --list              List previous pipeline runs
  --cleanup N         Clean up old runs, keeping last N runs

Examples:
  # Traditional ticket workflow (unchanged)
  python scripts/run_pipeline.py PROJ-123

  # Direct request with auto-detected project path
  cd /my/project
  python /path/to/gladius/scripts/run_pipeline.py "Add login button"

  # Direct request with explicit project path
  python scripts/run_pipeline.py "Fix memory leak" --project-path /my/project

  # Complex request with all options
  cd /my/project
  python gladius/scripts/run_pipeline.py "Refactor auth to use JWT" \
    --model opus --max-iterations 3 --timeout 600

  # List runs (shows both ticket and direct request runs)
  python scripts/run_pipeline.py --list

  # Cleanup old runs
  python scripts/run_pipeline.py --cleanup 10
```

### Usage Examples

```bash
# === BACKWARD COMPATIBLE (Unchanged) ===
python scripts/run_pipeline.py PROJ-123
python scripts/run_pipeline.py PROJ-456 --model opus

# === NEW: Direct Requests ===
# Simple direct request (auto-detects CWD as project path)
cd /my/webapp
python /path/to/gladius/scripts/run_pipeline.py "Add email validation"

# Direct request with explicit path
python scripts/run_pipeline.py "Fix bug in auth.py" --project-path /my/webapp

# Long direct request
cd /my/project
python gladius/scripts/run_pipeline.py \
  "Refactor the authentication system to use JWT tokens instead of sessions, \
   add refresh token support, and implement proper token rotation"

# === NEW: Combined Features ===
# Ultimate simplicity
cd /my/project && python /tools/gladius/scripts/run_pipeline.py "Add tests"

# With model selection
cd /my/app
python gladius/scripts/run_pipeline.py "Optimize database queries" --model opus

# All the bells and whistles
cd /my/webapp
python /tools/gladius/scripts/run_pipeline.py \
  "Add comprehensive error handling to user service" \
  --model opus --max-iterations 3 --timeout 600
```

---

## Implementation Phases

### Phase 1: Project Path Support (7.5 hours)
**Priority**: Highest - Foundation for both features

**Tasks**:
1. Create `src/utils/path_validator.py` with validation logic
2. Create `src/utils/path_resolver.py` with priority resolution
3. Write unit tests for path utilities (12 tests)
4. Update `config/settings.yaml` with path settings
5. Modify `src/orchestrator.py` to accept `project_path` parameter
6. Update CLI script to add `--project-path` argument
7. Update all 3 agents to include `project_path` in context
8. Update all 3 prompt files with project context guidance
9. Integration tests for path resolution (10 tests)

**Deliverables**:
- ✅ Working `--project-path` argument
- ✅ Auto-detection of current directory
- ✅ Path validation and error handling
- ✅ All agents receive project context
- ✅ 22 new tests passing

### Phase 2: Request Processing (7.5 hours)
**Priority**: High - Core feature

**Tasks**:
1. Create `src/request_processor/__init__.py`
2. Create `src/request_processor/request_parser.py` with type detection
3. Create `src/request_processor/request_adapter.py` with synthetic ticket creation
4. Create `src/request_processor/type_detector.py` with keyword analysis
5. Write unit tests for request processing (33 tests)
6. Create `src/mcp/unified_mcp_client.py` with dual mode support
7. Write unit tests for unified MCP client (12 tests)
8. Update orchestrator to use `request` parameter instead of `ticket_id`
9. Integration tests for request processing (8 tests)

**Deliverables**:
- ✅ Request type auto-detection
- ✅ Synthetic ticket generation
- ✅ Unified MCP client
- ✅ 53 new tests passing

### Phase 3: CLI Integration (4 hours)
**Priority**: High - User interface

**Tasks**:
1. Update CLI argument from `ticket_id` to `request`
2. Integrate `UnifiedMCPClient` into CLI script
3. Update help text and examples
4. Improve error messages for common failures
5. Update `list` command to show direct request indicators
6. Update `cleanup` command to handle DIRECT-* tickets
7. End-to-end CLI testing (20 manual scenarios)
8. Update README.md with new usage examples

**Deliverables**:
- ✅ Unified CLI interface
- ✅ Clear error messages
- ✅ Updated documentation
- ✅ All manual tests passing

### Phase 4: Documentation & Polish (6.5 hours)
**Priority**: Medium - Production readiness

**Tasks**:
1. Update `README.md` with both features
2. Update `QUICKSTART.md` with examples
3. Create `docs/DIRECT_REQUESTS.md` tutorial
4. Create `docs/PROJECT_PATH_USAGE.md` guide
5. Enhanced error handling with helpful suggestions
6. Add edge case handling (15 scenarios)
7. Comprehensive integration tests (23 tests)
8. Update `PROJECT_COMPLETE.md` with new features
9. Create example scripts (`examples/direct_requests.sh`)

**Deliverables**:
- ✅ Complete documentation suite
- ✅ Production-quality error handling
- ✅ All edge cases covered
- ✅ Example scripts

### Phase 5: Optional Enhancements (6 hours)
**Priority**: Low - Future nice-to-haves

**Tasks**:
1. Interactive mode for ambiguous requests
2. Request templates library
3. Shell script wrapper (`gladius` command)
4. Project structure auto-detection
5. File reading capability for Planner
6. Git integration hooks

**Deliverables**:
- Optional features for power users
- Enhanced user experience

---

## Testing Strategy

### Unit Tests (Total: ~67 tests)

**Path Utilities** (`tests/unit/test_path_validator.py` - 10 tests):
- test_validate_existing_directory
- test_validate_nonexistent_path_raises_error
- test_validate_file_not_directory_raises_error
- test_validate_no_read_permission_raises_error
- test_relative_path_converted_to_absolute
- test_symlink_resolution
- test_windows_path_handling
- test_unix_path_handling
- test_path_with_spaces
- test_path_with_special_characters

**Path Resolution** (`tests/unit/test_path_resolver.py` - 12 tests):
- test_cli_path_takes_priority
- test_cwd_used_when_no_cli_path
- test_config_fallback_when_no_cli_or_cwd
- test_cwd_detection_automatic
- test_invalid_cli_path_raises_error
- test_invalid_config_path_falls_back
- test_priority_order_correct
- test_resolve_with_all_sources
- test_resolve_with_minimal_sources
- test_resolve_validates_final_path
- test_relative_paths_resolved
- test_absolute_paths_pass_through

**Request Processing** (`tests/unit/test_request_parser.py` - 15 tests):
- test_parse_valid_ticket_id
- test_parse_natural_request
- test_parse_ticket_with_whitespace
- test_parse_empty_string
- test_parse_complex_ticket_format
- test_parse_lowercase_ticket_rejected
- test_parse_ticket_without_dash
- test_parse_multiline_request
- test_parse_long_request
- test_parse_request_with_special_chars
- test_parse_request_looks_like_ticket
- test_parse_multiple_sentences
- test_parse_unicode_characters
- test_parse_numeric_only
- test_parse_alphanumeric_only

**Request Adapter** (`tests/unit/test_request_adapter.py` - 10 tests):
- test_create_synthetic_ticket_basic
- test_synthetic_ticket_structure
- test_title_extraction_short_request
- test_title_extraction_long_request
- test_title_extraction_multiline
- test_type_detection_integration
- test_synthetic_ticket_id_format
- test_synthetic_ticket_id_uniqueness
- test_priority_override
- test_type_override

**Type Detector** (`tests/unit/test_type_detector.py` - 8 tests):
- test_detect_bug_keywords
- test_detect_feature_keywords
- test_detect_improvement_keywords
- test_detect_mixed_keywords
- test_detect_no_keywords_defaults_feature
- test_detect_case_insensitive
- test_detect_multiple_bugs_wins
- test_detect_from_context

**Unified MCP** (`tests/unit/test_unified_mcp.py` - 12 tests):
- test_ticket_id_delegates_to_ticket_mcp
- test_natural_request_creates_synthetic
- test_failed_ticket_lookup_fallback
- test_synthetic_ticket_has_required_fields
- test_ticket_marked_as_ticket_type
- test_natural_marked_as_natural_type
- test_health_check_delegates
- test_empty_request_handling
- test_nonexistent_ticket_fallback
- test_connection_error_fallback
- test_synthetic_ticket_flags
- test_adapter_integration

### Integration Tests (Total: ~23 tests)

**Direct Requests** (`tests/integration/test_direct_requests.py` - 8 tests):
- test_end_to_end_direct_request
- test_direct_request_creates_synthetic_ticket
- test_direct_request_with_all_agents
- test_direct_request_type_detection
- test_direct_request_artifacts_created
- test_direct_request_summary_correct
- test_list_shows_direct_requests
- test_cleanup_includes_direct_requests

**Project Path** (`tests/integration/test_project_path.py` - 10 tests):
- test_explicit_project_path
- test_auto_detect_cwd
- test_project_path_in_context
- test_project_path_in_summary
- test_project_path_in_agent_messages
- test_relative_path_resolution
- test_invalid_path_fails_early
- test_path_validation_messages
- test_project_path_with_spaces
- test_project_path_symlink

**Backward Compatibility** (`tests/integration/test_backward_compat.py` - 5 tests):
- test_ticket_id_still_works
- test_existing_mock_tickets_work
- test_existing_cli_flags_work
- test_list_and_cleanup_work
- test_no_regression_in_artifacts

### Manual Testing Checklist (20 scenarios)

```bash
# === Backward Compatibility ===
# 1. Traditional ticket workflow
python scripts/run_pipeline.py PROJ-123
# Expected: Works exactly as before

# 2. Ticket with all flags
python scripts/run_pipeline.py PROJ-456 --model opus --max-iterations 3
# Expected: All flags work as before

# === Project Path ===
# 3. Auto-detect current directory
cd /my/project
python gladius/scripts/run_pipeline.py PROJ-123
# Expected: Uses /my/project as project path

# 4. Explicit project path
python scripts/run_pipeline.py PROJ-123 --project-path /other/project
# Expected: Uses /other/project

# 5. Relative project path
python scripts/run_pipeline.py PROJ-123 --project-path ../sibling/project
# Expected: Resolves and validates relative path

# 6. Invalid project path
python scripts/run_pipeline.py PROJ-123 --project-path /nonexistent
# Expected: Clear error message about path not existing

# 7. File instead of directory
python scripts/run_pipeline.py PROJ-123 --project-path /path/to/file.py
# Expected: Error suggesting parent directory

# === Direct Requests ===
# 8. Simple direct request
cd /my/project
python gladius/scripts/run_pipeline.py "Add login button"
# Expected: Creates DIRECT-* ticket, runs pipeline

# 9. Bug-type request
python scripts/run_pipeline.py "Fix memory leak in auth service"
# Expected: Detects as "bug" type

# 10. Improvement-type request
python scripts/run_pipeline.py "Refactor database queries"
# Expected: Detects as "improvement" type

# 11. Long direct request
python scripts/run_pipeline.py "Create a comprehensive user authentication system with OAuth2, JWT, and session management"
# Expected: Truncates title, full text in description

# 12. Direct request with explicit path
python scripts/run_pipeline.py "Add tests" --project-path /my/project
# Expected: Uses explicit path, creates synthetic ticket

# === Edge Cases ===
# 13. Empty request
python scripts/run_pipeline.py ""
# Expected: Helpful error message

# 14. Ticket that doesn't exist
python scripts/run_pipeline.py "PROJ-999"
# Expected: Warning, treats as natural request

# 15. Multi-line request
python scripts/run_pipeline.py "Add feature
with multiple lines
of description"
# Expected: Handles multi-line, uses first line for title

# 16. Request with special characters
python scripts/run_pipeline.py "Fix bug in @user's $variable"
# Expected: Preserves special characters

# 17. Very long path
python scripts/run_pipeline.py PROJ-123 --project-path /very/long/path/to/nested/directories/project
# Expected: Handles long paths correctly

# === List & Cleanup ===
# 18. List with mix of tickets and requests
python scripts/run_pipeline.py --list
# Expected: Shows both PROJ-* and DIRECT-* runs

# 19. Filter list by DIRECT ticket
python scripts/run_pipeline.py --list --ticket-id DIRECT-20241217120000
# Expected: Filters to specific direct request run

# 20. Cleanup with direct requests
python scripts/run_pipeline.py --cleanup 5
# Expected: Cleans up both ticket and direct request runs
```

---

## Edge Cases & Error Handling

### Input Validation

**1. Empty or whitespace request**
```python
if not request or not request.strip():
    print("Error: Request cannot be empty")
    print("\nExamples:")
    print('  python scripts/run_pipeline.py "Add login button"')
    print('  python scripts/run_pipeline.py PROJ-123')
    sys.exit(1)
```

**2. Request looks like ticket but doesn't exist**
```python
try:
    ticket = mcp_client.get_ticket(request)
except ValueError:
    print(f"Warning: Ticket '{request}' not found in MCP.")
    print(f"Treating as natural language request...")
    # Fallback to synthetic ticket
```

**3. Very long request (>1000 chars)**
```python
if len(request) > 1000:
    print(f"Warning: Request is {len(request)} characters long.")
    print("Title will be truncated, full text in description.")
```

### Path Validation

**4. Non-existent path**
```python
raise ValueError(
    f"Project path does not exist: {path}\n"
    f"Current directory: {Path.cwd()}\n"
    f"Did you mean: {Path.cwd()}?"
)
```

**5. Path is file, not directory**
```python
raise ValueError(
    f"Project path must be a directory: {path}\n"
    f"This appears to be a file.\n"
    f"Did you mean the parent directory: {path.parent}?"
)
```

**6. No read permissions**
```python
raise ValueError(
    f"Cannot read project path: {path}\n"
    f"Please check file permissions.\n"
    f"Try: chmod +r {path}"
)
```

**7. Path with spaces or special characters**
```python
# Handle automatically with pathlib
path = Path(path_string)  # Handles spaces correctly
```

### Workflow Edge Cases

**8. CWD is not a project directory**
```python
# Allow - agent will work with whatever files exist
print(f"Warning: Current directory may not be a project root: {cwd}")
print("Proceeding anyway. Agents will work with available files.")
```

**9. Running from Gladius directory itself**
```python
if Path.cwd().name == "Google_Gladius":
    print("Warning: You're in the Gladius directory.")
    print("Did you mean to specify --project-path to your actual project?")
    print("Proceeding with current directory as project path...")
```

**10. Simultaneous runs**
```python
# Timestamp-based IDs ensure uniqueness
ticket_id = f"DIRECT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
# Milliseconds if needed:
# ticket_id = f"DIRECT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
```

---

## File Summary

### New Files to Create (11 files)

1. `src/request_processor/__init__.py`
2. `src/request_processor/request_parser.py`
3. `src/request_processor/request_adapter.py`
4. `src/request_processor/type_detector.py`
5. `src/utils/path_validator.py`
6. `src/utils/path_resolver.py`
7. `src/mcp/unified_mcp_client.py`
8. `tests/unit/test_path_validator.py`
9. `tests/unit/test_request_parser.py`
10. `tests/integration/test_direct_requests.py`
11. `docs/DIRECT_REQUESTS.md`

### Existing Files to Modify (10 files)

1. `scripts/run_pipeline.py` - Change to `request` arg, add path resolution
2. `src/orchestrator.py` - Accept `request` + `project_path`, validate path
3. `src/agents/planner_agent.py` - Include project_path in build_user_message
4. `src/agents/implementer_agent.py` - Include project_path in build_user_message
5. `src/agents/reviewer_agent.py` - Include project_path in build_user_message
6. `prompts/planner_prompt.txt` - Add project context guidance
7. `prompts/implementer_prompt.txt` - Add project context guidance
8. `prompts/reviewer_prompt.txt` - Add project context guidance
9. `config/settings.yaml` - Add direct request & path settings
10. `README.md` - Update with new usage examples

---

## Time Estimates

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1: Project Path Support | 7.5 hours | Path validation, resolution, integration |
| Phase 2: Request Processing | 7.5 hours | Parser, adapter, type detection, unified MCP |
| Phase 3: CLI Integration | 4 hours | CLI updates, help text, error messages |
| **Core Implementation (1-3)** | **19 hours** | **Minimum for working system** |
| Phase 4: Documentation & Polish | 6.5 hours | Docs, edge cases, integration tests |
| **Production Ready (1-4)** | **25.5 hours** | **Recommended for deployment** |
| Phase 5: Optional Enhancements | 6 hours | Interactive mode, templates, extras |
| **Full Implementation (1-5)** | **31.5 hours** | **Complete with all features** |

**Recommendation**: Implement Phases 1-4 (~3-4 working days) for a production-ready system.

---

## Success Criteria

### Functional Requirements
- ✅ Accept both ticket IDs (PROJ-123) and natural requests ("Add feature")
- ✅ Automatically detect current directory as project path
- ✅ Allow explicit project path override via --project-path
- ✅ Generate valid synthetic tickets for direct requests
- ✅ Auto-detect ticket type from keywords (bug, feature, improvement)
- ✅ Maintain 100% backward compatibility
- ✅ Work from any directory with any project

### Non-Functional Requirements
- ✅ Request processing adds <100ms overhead
- ✅ Path validation completes instantly (<10ms)
- ✅ Clear, actionable error messages for all failures
- ✅ Comprehensive test coverage (90+ tests)
- ✅ Complete documentation with examples
- ✅ Zero breaking changes to existing code

### User Experience
- ✅ Simple command: `cd /project && gladius "Add feature"`
- ✅ Works from any directory
- ✅ Intuitive request parsing
- ✅ Helpful error messages
- ✅ Backward compatible (existing scripts work unchanged)

---

## Next Steps

### To Begin Implementation

1. **Review this plan** - Confirm approach and scope
2. **Create feature branch** - `git checkout -b feature/direct-requests-and-path`
3. **Implement Phase 1** - Project path support (7.5 hours)
4. **Test Phase 1** - Validate path features work
5. **Implement Phase 2** - Request processing (7.5 hours)
6. **Test Phase 2** - Validate request features work
7. **Implement Phase 3** - CLI integration (4 hours)
8. **Implement Phase 4** - Documentation & polish (6.5 hours)
9. **Full testing** - Run all unit, integration, and manual tests
10. **Merge to main** - After all tests pass and docs updated

### Quick Start Testing (Current Workaround)

While implementation is in progress, you can test the concept with a workaround:

```bash
# Navigate to your project first
cd /path/to/your/project

# Then run pipeline (will use current directory)
python /path/to/Google_Gladius/scripts/run_pipeline.py PROJ-123

# This works but agents don't receive explicit project_path in context
```

---

**Status**: 📋 **Enhancement Plan Complete - Ready for Implementation**

**Priority**: **High** - Blocks real-world usage
**Complexity**: **Medium** - Clean extension of existing architecture
**Risk**: **Low** - Backward compatible with comprehensive testing
**Impact**: **High** - Transforms demo into production tool

**Estimated Effort**: 25.5 hours for production-ready implementation
**Recommended Start**: Phase 1 (Project Path Support)
