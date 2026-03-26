"""Implementer Agent - Generates code changes based on plan"""
from typing import Dict, Any
from pathlib import Path

from .base_agent import BaseAgent
from ..schemas.implementer_schema import ImplementerOutput


class ImplementerAgent(BaseAgent[ImplementerOutput]):
    """Agent that implements code changes based on the plan"""

    def __init__(self, *args, **kwargs):
        """Initialize Implementer Agent"""
        super().__init__(*args, **kwargs)

        # Load system prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "implementer_prompt.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    def get_system_prompt(self) -> str:
        """Get the implementer system prompt"""
        return self.system_prompt

    def build_user_message(self, context: Dict[str, Any]) -> str:
        """
        Build user message from ticket and plan context

        Args:
            context: Dict containing:
                - ticket: Ticket data from MCP
                - plan: PlannerOutput from planner agent
                - project_path: Path to project codebase (optional)
                - project_path_absolute: Absolute path to project (optional)
                - code_context: Optional code snippets or file contents
                - validation_feedback: Optional feedback from previous attempts

        Returns:
            Formatted user message
        """
        ticket = context['ticket']
        plan = context['plan']

        message = f"""# Implementation Task

## Original Ticket
**Ticket ID:** {ticket['key']}
**Title:** {ticket['title']}

{ticket['description']}

"""

        # Add project path context if available
        if context.get('project_path'):
            message += f"""## Project Context
**Project Path:** {context['project_path']}
**Absolute Path:** {context.get('project_path_absolute', context['project_path'])}

All file paths in your implementation should be relative to this project directory.

"""

        message += f"""## Implementation Plan
**Summary:** {plan.summary}

**Steps to Implement:**
"""
        for i, step in enumerate(plan.plan, 1):
            message += f"{i}. {step}\n"

        message += "\n**Files to Change:**\n"
        for file_change in plan.files_to_change:
            message += f"- `{file_change.path}`: {file_change.reason}\n"

        if plan.assumptions:
            message += "\n**Assumptions:**\n"
            for assumption in plan.assumptions:
                message += f"- {assumption}\n"

        if plan.risks:
            message += "\n**Risks to Consider:**\n"
            for risk in plan.risks:
                message += f"- {risk}\n"

        # Add code context if provided
        if context.get('code_context'):
            message += "\n## Existing Code Context\n"
            message += context['code_context']

        # Add validation feedback if this is a retry
        if context.get('validation_feedback'):
            message += "\n" + context['validation_feedback']

        message += "\n\nPlease implement the changes according to this plan. Generate complete, working code with proper error handling and tests."

        return message

    def get_output_schema(self) -> type[ImplementerOutput]:
        """Get the Pydantic output schema"""
        return ImplementerOutput
