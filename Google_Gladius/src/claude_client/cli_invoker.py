"""Claude CLI subprocess wrapper for invoking agents"""
import subprocess
import json
import re
from typing import Dict, Any, Optional
from pathlib import Path


class ClaudeClient:
    """Wrapper for invoking Claude CLI with JSON output"""

    def __init__(self, claude_path: str = "claude", timeout: int = 300):
        """
        Initialize Claude CLI client

        Args:
            claude_path: Path to Claude CLI executable (default: "claude")
            timeout: Timeout in seconds for CLI execution (default: 300)
        """
        self.claude_path = claude_path
        self.timeout = timeout

    def invoke(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        model: str = "sonnet"
    ) -> Dict[str, Any]:
        """
        Invoke Claude CLI and return JSON output

        Args:
            user_message: The user message/prompt
            system_prompt: Optional system prompt
            json_schema: Optional JSON schema for output validation
            model: Model to use (sonnet, opus, haiku)

        Returns:
            Parsed JSON output from Claude

        Raises:
            subprocess.TimeoutExpired: If execution exceeds timeout
            json.JSONDecodeError: If output is not valid JSON
            RuntimeError: If Claude CLI execution fails
        """
        cmd = [
            self.claude_path,
            '--print',
            '--no-session-persistence',
            '--model', model
        ]

        # Add system prompt if provided
        if system_prompt:
            cmd.extend(['--system-prompt', system_prompt])

        # Add JSON schema if provided
        if json_schema:
            cmd.extend([
                '--output-format', 'json',
                '--json-schema', json.dumps(json_schema)
            ])

        # Add user message
        cmd.append(user_message)

        try:
            # Run with stdin/stderr passthrough for interactive auth (AWS SSO)
            # Only capture stdout for JSON parsing
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=None,  # Allow stderr passthrough for auth prompts
                stdin=None,   # Allow stdin passthrough for interactive input
                text=True,
                timeout=self.timeout,
                check=True
            )

            # Debug: Print to stderr so it shows up (stdout is captured)
            import sys
            print(f"\n[DEBUG] About to parse stdout, length: {len(result.stdout)}", file=sys.stderr)

            # Parse JSON output
            parsed_result = self._parse_json_output(result.stdout)

            # Debug: Show what we got after parsing
            print(f"[DEBUG] Parse result type: {type(parsed_result)}", file=sys.stderr)
            if isinstance(parsed_result, dict):
                print(f"[DEBUG] Parse result keys: {list(parsed_result.keys())[:10]}", file=sys.stderr)

            return parsed_result

        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"Claude CLI execution exceeded timeout of {self.timeout}s"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Claude CLI execution failed with return code {e.returncode}"
            )

    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """
        Parse JSON output, handling markdown-wrapped JSON and Claude CLI response wrappers

        Args:
            output: Raw output from Claude CLI

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If no valid JSON found
        """
        # Debug: Print raw output for troubleshooting (to stderr so it shows)
        import sys
        print(f"\n[DEBUG] Raw Claude CLI output (first 500 chars):", file=sys.stderr)
        print(output[:500], file=sys.stderr)
        print(f"[DEBUG] Output type: {type(output)}, Length: {len(output)}", file=sys.stderr)

        # Try direct JSON parse first
        try:
            parsed = json.loads(output)
            print(f"[DEBUG] Parsed JSON successfully. Top-level keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not a dict'}", file=sys.stderr)

            # Check if this is a Claude CLI response wrapper
            # Format: {'type': 'result', 'subtype': ..., 'content': [...] or 'structured_output': {...}}
            if isinstance(parsed, dict):
                # Extract content from wrapper if present
                if 'type' in parsed and parsed.get('type') == 'result':
                    print(f"[DEBUG] Detected wrapper format with type='result'", file=sys.stderr)

                    # First check for structured_output field (used by --output-format json)
                    if 'structured_output' in parsed:
                        structured_output = parsed['structured_output']
                        print(f"[DEBUG] Found 'structured_output' field, type: {type(structured_output)}", file=sys.stderr)
                        if isinstance(structured_output, dict):
                            print(f"[DEBUG] Returning structured_output directly", file=sys.stderr)
                            return structured_output

                    # Look for actual content in various possible fields
                    for content_field in ['content', 'data', 'text', 'output']:
                        if content_field in parsed:
                            content = parsed[content_field]
                            print(f"[DEBUG] Found content field '{content_field}', type: {type(content)}", file=sys.stderr)

                            # If content is a list, look for text blocks
                            if isinstance(content, list):
                                print(f"[DEBUG] Content is list with {len(content)} items", file=sys.stderr)
                                for i, item in enumerate(content):
                                    if isinstance(item, dict):
                                        print(f"[DEBUG] Item {i} keys: {list(item.keys())}", file=sys.stderr)
                                        # Look for text field in content items
                                        if 'text' in item:
                                            text_content = item['text']
                                            print(f"[DEBUG] Found text field in item {i}, first 200 chars: {text_content[:200]}", file=sys.stderr)

                                            # Try parsing as JSON directly
                                            try:
                                                extracted = json.loads(text_content)
                                                print(f"[DEBUG] Successfully extracted JSON from text field!", file=sys.stderr)
                                                return extracted
                                            except (json.JSONDecodeError, TypeError) as e:
                                                print(f"[DEBUG] Failed to parse text as JSON: {e}", file=sys.stderr)

                                                # Try extracting from markdown code block in text
                                                md_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                                                md_match = re.search(md_pattern, text_content, re.DOTALL)
                                                if md_match:
                                                    print(f"[DEBUG] Found markdown code block in text field", file=sys.stderr)
                                                    try:
                                                        extracted = json.loads(md_match.group(1))
                                                        print(f"[DEBUG] Successfully extracted JSON from markdown!", file=sys.stderr)
                                                        return extracted
                                                    except json.JSONDecodeError:
                                                        print(f"[DEBUG] Failed to parse markdown JSON", file=sys.stderr)
                                                        pass

                            # If content is a string, try to parse it
                            elif isinstance(content, str):
                                print(f"[DEBUG] Content is string, attempting to parse...", file=sys.stderr)
                                try:
                                    return json.loads(content)
                                except json.JSONDecodeError:
                                    pass

                            # If content is already a dict, return it
                            elif isinstance(content, dict):
                                print(f"[DEBUG] Content is dict, returning as-is", file=sys.stderr)
                                return content

                # If no wrapper detected or extraction failed, return as-is
                print(f"[DEBUG] No wrapper extraction successful, returning parsed as-is", file=sys.stderr)
                # Dump full structure for debugging
                print(f"[DEBUG] Full parsed structure: {json.dumps(parsed, indent=2)[:1000]}", file=sys.stderr)
                return parsed

            return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        # Matches: ```json\n{...}\n``` or ```\n{...}\n```
        pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(pattern, output, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in text
        # Look for {...} pattern
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, output, re.DOTALL)

        for potential_json in matches:
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError:
                continue

        raise json.JSONDecodeError(
            f"No valid JSON found in output: {output[:200]}...",
            output,
            0
        )
