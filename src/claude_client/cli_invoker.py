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

# Regex patterns for extracting JSON from text
MD_JSON_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
JSON_BRACE_PATTERN = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)

# Keys that indicate a JSON object is one of our target responses
TARGET_KEYS = {'plan', 'changes', 'verdict', 'issues', 'patch', 'files_to_modify', 'files_to_change'}


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

        # Add user message safely around Windows limitations
        import sys
        cmd_length = sum(len(str(x)) for x in cmd) + len(user_message or "")
        user_msg_temp = None
        stdin_val = None

        if sys.platform == "win32" and cmd_length > 8000:
            import tempfile
            import os
            fd, user_msg_temp = tempfile.mkstemp(suffix=".txt", text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(user_message)
            
            # Shorten the command line explicitly, relying on Claude to read stdin
            cmd.append("Please fulfill the task provided in the standard input.")
            stdin_val = open(user_msg_temp, 'r', encoding='utf-8')
        else:
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
                stdin=stdin_val,   # Usually None, but file pointer if WinError 206 limits exceeded
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
        finally:
            if stdin_val:
                try:
                    stdin_val.close()
                except Exception:
                    pass
            if user_msg_temp:
                import os
                if os.path.exists(user_msg_temp):
                    try:
                        os.remove(user_msg_temp)
                    except Exception:
                        pass

    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """
        Parse JSON output, handling markdown-wrapped JSON, Claude CLI response wrappers, and AWS SSO preambles
        """
        logger.debug(f"Raw Claude CLI output (first 500 chars):\n{output[:500]}")

        def extract_from_string(s: str) -> Optional[Dict[str, Any]]:
            try:
                obj = json.loads(s)
                if isinstance(obj, dict) and any(k in obj for k in TARGET_KEYS):
                    return obj
            except json.JSONDecodeError:
                pass
            
            md_match = MD_JSON_PATTERN.search(s)
            if md_match:
                try:
                    obj = json.loads(md_match.group(1))
                    if isinstance(obj, dict) and any(k in obj for k in TARGET_KEYS):
                        return obj
                except json.JSONDecodeError:
                    pass
            
            matches = JSON_BRACE_PATTERN.findall(s)
            for m in matches:
                try:
                    obj = json.loads(m)
                    if isinstance(obj, dict) and any(k in obj for k in TARGET_KEYS):
                        return obj
                except json.JSONDecodeError:
                    continue
            return None

        def search_parsed(obj: Any) -> Optional[Dict[str, Any]]:
            if isinstance(obj, dict):
                if any(k in obj for k in TARGET_KEYS):
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

        # First, see if the entire raw string can directly yield the schema we want
        direct_extract = extract_from_string(output)
        if direct_extract:
            return direct_extract

        # Attempt to parse whatever JSON wrapper we can find
        parsed = None
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            matches = JSON_BRACE_PATTERN.findall(output)
            for m in matches:
                try:
                    parsed = json.loads(m)
                    break
                except json.JSONDecodeError:
                    continue

        if parsed is not None:
            # Always prefer natively parsed structured_output from the CLI wrapper
            # to avoid grabbing unvalidated text/markdown conversational drafts.
            if isinstance(parsed, dict):
                struct_out = parsed.get("structured_output")
                if isinstance(struct_out, dict):
                    return struct_out
                # Fallback to older wrapper styles
                if parsed.get("type") == "result" and isinstance(parsed.get("result"), dict):
                    if "structured_output" in parsed["result"]:
                        return parsed["result"]["structured_output"]

            found_schema = search_parsed(parsed)
            if found_schema:
                logger.debug("Successfully extracted target schema from parsed wrapper.")
                return found_schema
            return parsed

        raise json.JSONDecodeError(
            f"No valid JSON found in output: {output[:200]}...",
            output,
            0
        )
