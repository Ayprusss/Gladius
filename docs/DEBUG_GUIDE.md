# Debug Guide: Pydantic Validation Issue

## Current Status

The Pydantic validation error is still occurring. I've added comprehensive debug logging to help diagnose the exact issue.

---

## Step 1: Run the Debug Script

Run this simple test to see what Claude CLI is actually returning:

```bash
cd c:\Code\hackathon-projects-and-ideas\Google_Gladius
python debug_claude_cli.py
```

This will:
1. Make a simple Claude CLI invocation
2. Print detailed debug output showing:
   - Raw Claude CLI output
   - Parsed JSON structure
   - Wrapper detection process
   - Extraction attempts
3. Try Pydantic validation and report success/failure

**Please run this and share the full output with me.**

---

## Step 2: Run the Full Pipeline with Debug Output

Try running your original command again:

```bash
cd /your/project
python c:\Code\hackathon-projects-and-ideas\Google_Gladius\scripts\run_pipeline.py "Add feature description"
```

Now you'll see `[DEBUG]` messages showing:
- What Claude CLI returns (first 500 chars)
- Whether wrapper format is detected
- What extraction method is tried
- Success or failure of each step

**Look for the DEBUG output and share it with me.**

---

## What to Look For in Debug Output

### Expected Good Output

```
[DEBUG] Raw Claude CLI output (first 500 chars):
{"type": "result", "content": [{"text": "{\"summary\": \"...\", \"plan\": [...]}"}]}
...
[DEBUG] Detected wrapper format with type='result'
[DEBUG] Found content field 'content', type: <class 'list'>
[DEBUG] Successfully extracted JSON from text field!
```

### Possible Bad Outputs

#### Case 1: No Wrapper Detected
```
[DEBUG] Parsed JSON successfully. Top-level keys: [...]
[DEBUG] No wrapper extraction successful, returning parsed as-is
```
→ Means the response doesn't match our wrapper detection

#### Case 2: Wrapper But No Text Field
```
[DEBUG] Detected wrapper format with type='result'
[DEBUG] Found content field 'content', type: <class 'list'>
[DEBUG] Item 0 keys: ['type', 'something_else']
```
→ Means the structure is different than expected

#### Case 3: Text Field But JSON Parse Fails
```
[DEBUG] Found text field in item 0, first 200 chars: ...
[DEBUG] Failed to parse text as JSON: ...
```
→ Means the text content isn't valid JSON

---

## Step 3: Check Claude CLI Version

The response format might have changed. Check your Claude CLI version:

```bash
claude --version
```

If it's a very recent version, the output format may have changed.

---

## Step 4: Manual Test

You can also manually test Claude CLI to see what it outputs:

```bash
claude --print --no-session-persistence --model sonnet --output-format json --json-schema '{"type":"object","properties":{"test":{"type":"string"}},"required":["test"]}' "Return JSON with test field"
```

This should help us see the exact format Claude CLI uses.

---

## Common Issues and Solutions

### Issue 1: Text Field Contains Markdown

**Symptom:** Debug shows text starts with "```json"

**Solution:** Already handled - the code now extracts from markdown blocks

### Issue 2: Different Wrapper Structure

**Symptom:** Debug shows different keys than expected

**Solution:** Share the debug output - I'll update the parser

### Issue 3: Multiple Content Items

**Symptom:** Debug shows multiple items in content list, not all are JSON

**Solution:** The code should iterate through all items - check if it's finding the right one

### Issue 4: No JSON Schema Support

**Symptom:** Claude CLI doesn't respect --json-schema flag

**Solution:** May need to use prompt engineering instead of schema

---

## Quick Fix Options

While we debug, here are some temporary workarounds:

### Option A: Skip Schema Validation
Edit `src/agents/base_agent.py` around line 103:

```python
# Temporary workaround: print raw output for debugging
print(f"[TEMP DEBUG] Raw agent output: {raw_output}")

# Skip validation temporarily
# validated_output = schema_class.model_validate(raw_output)
# Instead, use raw_output directly (UNSAFE - TEMP ONLY)
```

### Option B: Use Mock MCP Only
Edit `config/settings.yaml`:

```yaml
mcp:
  type: "mock"  # Instead of "unified"
```

This uses the mock ticket system which doesn't invoke Claude CLI.

---

## Next Steps

1. **Run the debug script** (`python debug_claude_cli.py`)
2. **Share the full debug output** with me
3. **I'll analyze the actual format** Claude CLI is returning
4. **I'll update the parser** to handle the actual format

The debug output will show us exactly what's happening and allow me to fix it properly.

---

## Files with Debug Logging

- [src/claude_client/cli_invoker.py](src/claude_client/cli_invoker.py) - Added `[DEBUG]` prints
- [debug_claude_cli.py](debug_claude_cli.py) - Simple test script

Once we identify the issue, I'll remove the debug output and implement the proper fix.

---

## Contact Point

After running the debug script, please share:
1. The complete console output
2. Your Claude CLI version (`claude --version`)
3. Any error messages you see

This will help me pinpoint the exact issue and fix it properly.
