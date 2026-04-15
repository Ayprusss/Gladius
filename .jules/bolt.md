## 2024-04-14 - Fix ReDoS vulnerability in JSON parsing

**Learning:**
I discovered a significant performance bottleneck (and potential ReDoS vulnerability) in how `ClaudeClient` was extracting JSON blocks from the raw Claude CLI output. The code was using `re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', s, re.DOTALL)` which uses catastrophic backtracking and hangs entirely on unbalanced or heavily nested sequences. Because LLM outputs are unpredictable and can easily contain unbalanced braces in code examples or reasoning blocks, this was a critical flaw that would silently fail and consume CPU on large outputs.

**Action:**
I completely replaced the regex string-matching approach with iterative parsing using Python's native `json.JSONDecoder().raw_decode()`. Next time I need to extract structured JSON out of unstructured text, I will skip regex altogether in favor of `raw_decode`, which correctly handles escape sequences and arbitrarily deep nesting in O(N) time without backtracking risks.
## 2026-04-15 - Remove time.sleep in ticket batch creation
**Learning:** Using `time.sleep()` to guarantee unique IDs is a major anti-pattern that slows down batch operations to O(N) time (1.1s per item in this case). Relying solely on second-level precision timestamps for uniqueness creates collisions when processes run quickly.
**Action:** Use microsecond precision (`%f`) combined with an iteration suffix to generate unique IDs synchronously without any blocking delays.
