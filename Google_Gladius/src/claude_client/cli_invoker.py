"""Claude CLI subprocess wrapper for invoking agents"""
import subprocess
import json
import re
import logging
import threading
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
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

    def _spinner_thread(self, stop_event: threading.Event):
        """
        Displays a spinning cursor in the console while waiting.
        """
        spinner_chars = ['-', '\\', '|', '/']
        i = 0
        while not stop_event.is_set():
            print(f"\rWaiting for Claude CLI... {spinner_chars[i % len(spinner_chars)]}", end="", flush=True)
            i += 1
            time.sleep(0.1)
        # Clear the spinner line after stopping
        print("\r" + " " * 40 + "\r", end="", flush=True)

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

        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=self._spinner_thread, args=(stop_spinner,))
        spinner_thread.daemon = True # Allow main program to exit even if spinner is still running
        spinner_thread.start()

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

            stop_spinner.set()
            spinner_thread.join() # Wait for spinner to finish clearing its line

            # Debug: Print to debug log
            logger.debug(f"About to parse stdout, length: {len(result.stdout)}")

            # Parse JSON output
            parsed_result = self._parse_json_output(result.stdout)

            # Debug: Show what we got after parsing
            logger.debug(f"Parse result type: {type(parsed_result)}")
            if isinstance(parsed_result, dict):
                logger.debug(f"Parse result keys: {list(parsed_result.keys())[:10]}")

            return parsed_result

        except subprocess.TimeoutExpired:
            stop_spinner.set()
            spinner_thread.join()
            raise TimeoutError(
                f"Claude CLI execution exceeded timeout of {self.timeout}s"
            )
        except subprocess.CalledProcessError as e:
            stop_spinner.set()
            spinner_thread.join()
            raise RuntimeError(
                f"Claude CLI execution failed with return code {e.returncode}"
            )
        except Exception as e:
            # Ensure spinner is stopped even for unexpected errors
            stop_spinner.set()
            spinner_thread.join()
            raise # Re-raise the exception

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
        # Debug: Print raw output for troubleshooting
        logger.debug(f"Raw Claude CLI output (first 500 chars):\n{output[:500]}")
        logger.debug(f"Output type: {type(output)}, Length: {len(output)}")

        # Try direct JSON parse first
        try:
            parsed = json.loads(output)
            logger.debug(f"Parsed JSON successfully. Top-level keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not a dict'}")

            # Check if this is a Claude CLI response wrapper
            if isinstance(parsed, dict):
                if 'type' in parsed and parsed.get('type') == 'result':
                    logger.debug("Detected wrapper format with type='result'")

                    if 'structured_output' in parsed:
                        structured_output = parsed['structured_output']
                        logger.debug(f"Found 'structured_output' field, type: {type(structured_output)}")
                        if isinstance(structured_output, dict):
                            return structured_output

                    for content_field in ['content', 'data', 'text', 'output']:
                        if content_field in parsed:
                            content = parsed[content_field]
                            logger.debug(f"Found content field '{content_field}', type: {type(content)}")

                            if isinstance(content, list):
                                for i, item in enumerate(content):
                                    if isinstance(item, dict) and 'text' in item:
                                        text_content = item['text']
                                        logger.debug(f"Found text field in item {i}, first 200 chars: {text_content[:200]}")
                                        try:
                                            extracted = json.loads(text_content)
                                            logger.debug("Successfully extracted JSON from text field!")
                                            return extracted
                                        except (json.JSONDecodeError, TypeError) as e:
                                            logger.debug(f"Failed to parse text as JSON: {e}")
                                            md_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                                            md_match = re.search(md_pattern, text_content, re.DOTALL)
                                            if md_match:
                                                try:
                                                    extracted = json.loads(md_match.group(1))
                                                    logger.debug("Successfully extracted JSON from markdown!")
                                                    return extracted
                                                except json.JSONDecodeError:
                                                    pass

                            elif isinstance(content, str):
                                try:
                                    return json.loads(content)
                                except json.JSONDecodeError:
                                    pass

                            elif isinstance(content, dict):
                                return content

                logger.debug("No wrapper extraction successful, returning parsed as-is")
                logger.debug(f"Full parsed structure: {json.dumps(parsed, indent=2)[:1000]}")
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
