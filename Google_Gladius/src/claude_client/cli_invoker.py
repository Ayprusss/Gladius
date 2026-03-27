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

            # Define target keys that identify our actual agent schemas
            target_keys = {'plan', 'changes', 'verdict', 'issues', 'patch', 'files_to_modify'}

            def extract_from_string(s: str) -> Optional[Dict[str, Any]]:
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict) and any(k in obj for k in target_keys):
                        return obj
                except json.JSONDecodeError:
                    pass
                md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.DOTALL)
                if md_match:
                    try:
                        obj = json.loads(md_match.group(1))
                        if isinstance(obj, dict) and any(k in obj for k in target_keys):
                            return obj
                    except json.JSONDecodeError:
                        pass
                return None

            def search_parsed(obj: Any) -> Optional[Dict[str, Any]]:
                if isinstance(obj, dict):
                    if any(k in obj for k in target_keys):
                        return obj
                    for v in obj.values():
                        res = search_parsed(v)
                        if res: return res
                elif isinstance(obj, list):
                    for v in obj:
                        res = search_parsed(v)
                        if res: return res
                elif isinstance(obj, str):
                    res = extract_from_string(obj)
                    if res: return res
                return None

            # Attempt a deep search for the target schema
            found_schema = search_parsed(parsed)
            if found_schema:
                logger.debug("Successfully extracted target schema from parsed wrapper.")
                return found_schema

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
