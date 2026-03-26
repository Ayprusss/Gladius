"""Reviewer Agent - Reviews implementation for quality and correctness"""
from typing import Dict, Any
from pathlib import Path

from .base_agent import BaseAgent
from ..schemas.reviewer_schema import ReviewerOutput


class ReviewerAgent(BaseAgent[ReviewerOutput]):
    """Agent that reviews implementation quality"""

    def __init__(self, *args, **kwargs):
        """Initialize Reviewer Agent"""
        super().__init__(*args, **kwargs)

        # Load system prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "reviewer_prompt.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    def get_system_prompt(self) -> str:
        """Get the reviewer system prompt"""
        return self.system_prompt

    def build_user_message(self, context: Dict[str, Any]) -> str:
        """
        Build user message from ticket, plan, and implementation context

        Args:
            context: Dict containing:
                - ticket: Ticket data from MCP
                - plan: PlannerOutput from planner agent
                - implementation: ImplementerOutput from implementer agent
                - project_path: Path to project codebase (optional)
                - project_path_absolute: Absolute path to project (optional)
                - validation_feedback: Optional feedback from previous attempts

        Returns:
            Formatted user message
        """
        ticket = context['ticket']
        plan = context['plan']
        implementation = context['implementation']

        message = f"""# Code Review Task

## Original Ticket
**Ticket ID:** {ticket['key']}
**Title:** {ticket['title']}
**Type:** {ticket.get('type', 'unknown')}
**Priority:** {ticket.get('priority', 'unknown')}

### Requirements
{ticket['description']}

"""

        # Add project path context if available
        if context.get('project_path'):
            message += f"""### Project Context
**Project Path:** {context['project_path']}
**Absolute Path:** {context.get('project_path_absolute', context['project_path'])}

When reviewing the implementation, consider the project structure and context at this location.

"""

        # Add acceptance criteria
        if ticket.get('acceptance_criteria'):
            message += "### Acceptance Criteria\n"
            for criterion in ticket['acceptance_criteria']:
                message += f"- {criterion}\n"
            message += "\n"

        # Add plan summary
        message += f"""## Implementation Plan
**Summary:** {plan.summary}

**Key Steps:**
"""
        for i, step in enumerate(plan.plan[:5], 1):  # Show first 5 steps
            message += f"{i}. {step}\n"

        if len(plan.plan) > 5:
            message += f"... and {len(plan.plan) - 5} more steps\n"

        # Add identified risks
        if plan.risks:
            message += "\n**Identified Risks:**\n"
            for risk in plan.risks:
                message += f"- {risk}\n"

        # Add implementation details
        message += f"""
## Implementation to Review

### Changes Made
"""
        for change in implementation.changes:
            message += f"- **{change.file}** ({change.type}): {change.description}\n"

        message += f"""
### Implementation Notes
{implementation.notes}

### Code Patch
```diff
{implementation.patch}
```

### Tests
"""
        if implementation.tests_added_or_updated:
            for test_file in implementation.tests_added_or_updated:
                message += f"- {test_file}\n"
        else:
            message += "- No tests mentioned\n"

        # Add validation feedback if this is a retry
        if context.get('validation_feedback'):
            message += "\n" + context['validation_feedback']

        message += """

Please perform a thorough code review. Check for:
1. Correctness - Does it solve the problem?
2. Security - Any vulnerabilities?
3. Error handling - Are errors handled properly?
4. Code quality - Is it maintainable?
5. Testing - Is coverage adequate?
6. Performance - Any obvious issues?

Provide specific, actionable feedback with severity levels."""

        return message

    def get_output_schema(self) -> type[ReviewerOutput]:
        """Get the Pydantic output schema"""
        return ReviewerOutput
