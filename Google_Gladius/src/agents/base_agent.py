"""Base agent class with common functionality"""
from abc import ABC, abstractmethod
from typing import Dict, Any, TypeVar, Generic
import time
import json
from pathlib import Path
from pydantic import BaseModel, ValidationError

from ..claude_client.cli_invoker import ClaudeClient


T = TypeVar('T', bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """Abstract base class for all agents"""

    def __init__(
        self,
        claude_client: ClaudeClient,
        max_retries: int = 3,
        base_delay: float = 2.0
    ):
        """
        Initialize base agent

        Args:
            claude_client: Claude CLI client instance
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay for exponential backoff in seconds (default: 2.0)
        """
        self.claude_client = claude_client
        self.max_retries = max_retries
        self.base_delay = base_delay

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent

        Returns:
            System prompt text
        """
        pass

    @abstractmethod
    def build_user_message(self, context: Dict[str, Any]) -> str:
        """
        Build user message from context

        Args:
            context: Context dictionary with ticket data, previous outputs, etc.

        Returns:
            Formatted user message
        """
        pass

    @abstractmethod
    def get_output_schema(self) -> type[T]:
        """
        Get the Pydantic model class for output validation

        Returns:
            Pydantic model class
        """
        pass

    def execute(self, context: Dict[str, Any]) -> T:
        """
        Execute the agent with retry logic

        Args:
            context: Context dictionary with inputs

        Returns:
            Validated agent output

        Raises:
            RuntimeError: If all retries are exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Build prompt
                user_message = self.build_user_message(context)
                system_prompt = self.get_system_prompt()

                # Get JSON schema from Pydantic model
                schema_class = self.get_output_schema()
                json_schema = schema_class.model_json_schema()

                # Invoke Claude CLI
                raw_output = self.claude_client.invoke(
                    user_message=user_message,
                    system_prompt=system_prompt,
                    json_schema=json_schema,
                    model=context.get('model', 'sonnet')
                )

                # Debug: Show what we got before validation (to stderr)
                import sys
                print(f"\n[DEBUG - BaseAgent] Raw output type: {type(raw_output)}", file=sys.stderr)
                print(f"[DEBUG - BaseAgent] Raw output keys: {list(raw_output.keys()) if isinstance(raw_output, dict) else 'not a dict'}", file=sys.stderr)
                if isinstance(raw_output, dict):
                    print(f"[DEBUG - BaseAgent] Has 'summary'? {('summary' in raw_output)}", file=sys.stderr)
                    print(f"[DEBUG - BaseAgent] Has 'plan'? {('plan' in raw_output)}", file=sys.stderr)
                    print(f"[DEBUG - BaseAgent] Has 'type'? {('type' in raw_output)}", file=sys.stderr)

                # Validate with Pydantic
                validated_output = schema_class.model_validate(raw_output)

                return validated_output

            except ValidationError as e:
                last_error = e
                error_details = str(e)

                if attempt < self.max_retries - 1:
                    # Add validation feedback to context for next attempt
                    feedback = f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION:\n{error_details}\n\nPlease ensure your response matches the required schema exactly."
                    context['validation_feedback'] = feedback

                    # Exponential backoff
                    delay = self.base_delay ** attempt
                    time.sleep(delay)

                    print(f"Attempt {attempt + 1} failed validation. Retrying in {delay}s...")
                else:
                    print(f"All {self.max_retries} attempts exhausted")

            except (json.JSONDecodeError, TimeoutError, RuntimeError) as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = self.base_delay ** attempt
                    time.sleep(delay)
                    print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                else:
                    print(f"All {self.max_retries} attempts exhausted")

        # All retries exhausted
        raise RuntimeError(
            f"Agent execution failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def persist_output(self, output: T, output_path: Path) -> None:
        """
        Persist agent output to file

        Args:
            output: Validated agent output
            output_path: Path to save output JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output.model_dump(), f, indent=2)

        print(f"Output saved to: {output_path}")
