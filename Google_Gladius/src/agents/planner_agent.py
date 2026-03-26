"""Planner Agent - Converts tickets into actionable plans"""
from typing import Dict, Any
from pathlib import Path

from .base_agent import BaseAgent
from ..schemas.planner_schema import PlannerOutput


class PlannerAgent(BaseAgent[PlannerOutput]):
    """Agent that creates implementation plans from tickets"""

    def __init__(self, *args, **kwargs):
        """Initialize Planner Agent"""
        super().__init__(*args, **kwargs)

        # Load system prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "planner_prompt.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    def get_system_prompt(self) -> str:
        """Get the planner system prompt"""
        return self.system_prompt

    def build_user_message(self, context: Dict[str, Any]) -> str:
        """
        Build user message from ticket context

        Args:
            context: Dict containing:
                - ticket: Ticket data from MCP
                - project_path: Path to project codebase (optional)
                - project_path_absolute: Absolute path to project (optional)
                - validation_feedback: Optional feedback from previous attempts

        Returns:
            Formatted user message
        """
        ticket = context['ticket']

        message = f"""# Ticket to Plan

**Ticket ID:** {ticket['key']}
**Title:** {ticket['title']}
**Type:** {ticket.get('type', 'unknown')}
**Priority:** {ticket.get('priority', 'unknown')}

## Description
{ticket['description']}

"""

        # Add project path context if available
        if context.get('project_path'):
            message += f"""## Project Context
**Project Path:** {context['project_path']}
**Absolute Path:** {context.get('project_path_absolute', context['project_path'])}

When creating your plan, consider that you will have access to files and context from this project directory.

"""

        # Add acceptance criteria if available
        if ticket.get('acceptance_criteria'):
            message += "## Acceptance Criteria\n"
            for criterion in ticket['acceptance_criteria']:
                message += f"- {criterion}\n"
            message += "\n"

        # Add comments if available
        if ticket.get('comments'):
            message += "## Comments\n"
            for comment in ticket['comments']:
                author = comment.get('author', 'unknown')
                text = comment.get('text', '')
                message += f"**{author}:** {text}\n"
            message += "\n"

        # Add related tickets if available
        if ticket.get('related_tickets'):
            message += f"## Related Tickets\n{', '.join(ticket['related_tickets'])}\n\n"

        # Add validation feedback if this is a retry
        if context.get('validation_feedback'):
            message += context['validation_feedback']

        message += "\nPlease create a detailed implementation plan for this ticket."

        return message

    def get_output_schema(self) -> type[PlannerOutput]:
        """Get the Pydantic output schema"""
        return PlannerOutput
