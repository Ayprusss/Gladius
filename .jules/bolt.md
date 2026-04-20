## 2024-04-14 - Fix ReDoS vulnerability in JSON parsing

**Learning:**
I discovered a significant performance bottleneck (and potential ReDoS vulnerability) in how `ClaudeClient` was extracting JSON blocks from the raw Claude CLI output. The code was using `re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', s, re.DOTALL)` which uses catastrophic backtracking and hangs entirely on unbalanced or heavily nested sequences. Because LLM outputs are unpredictable and can easily contain unbalanced braces in code examples or reasoning blocks, this was a critical flaw that would silently fail and consume CPU on large outputs.

**Action:**
I completely replaced the regex string-matching approach with iterative parsing using Python's native `json.JSONDecoder().raw_decode()`. Next time I need to extract structured JSON out of unstructured text, I will skip regex altogether in favor of `raw_decode`, which correctly handles escape sequences and arbitrarily deep nesting in O(N) time without backtracking risks.
## 2026-04-15 - Remove time.sleep in ticket batch creation
**Learning:** Using `time.sleep()` to guarantee unique IDs is a major anti-pattern that slows down batch operations to O(N) time (1.1s per item in this case). Relying solely on second-level precision timestamps for uniqueness creates collisions when processes run quickly.
**Action:** Use microsecond precision (`%f`) combined with an iteration suffix to generate unique IDs synchronously without any blocking delays.
## 2024-04-16 - Pre-compile static regexes
**Learning:** I found that we were repeatedly compiling static regex patterns inside frequently called functions (like extracting JSON and parsing tickets). Recompiling regex patterns on every method call is an unnecessary performance hit.
**Action:** Pre-compile regex strings at the module or class level (`re.compile()`) to avoid redundant compilation overhead and improve overall application execution speed.
## 2024-04-17 - Avoid redundant method calls in get_confidence

**Learning:** I found that `RequestTypeDetector.get_confidence` was redundantly calling `detect_type`, effectively performing O(N) operations over the string (lower-casing and keyword counting) twice for every call.
**Action:** Extract or inline the shared logic so `get_confidence` directly computes the result from scores it has already built, saving duplicate execution.
## 2024-05-18 - JSONDecoder memory copying anti-pattern
**Learning:** Using `json.JSONDecoder().raw_decode(s[start:])` in a loop to extract JSON from unstructured text is an anti-pattern. Slicing the string `s[start:]` creates a new string object in memory for each iteration, resulting in O(N^2) time complexity.
**Action:** Always use the `idx` parameter of `raw_decode`: `raw_decode(s, start)`. This decodes directly from the original string buffer. Remember that when using the `idx` parameter, the returned `index` is absolute, so the update step should be `start = index`, not `start += index`.

## 2024-05-18 - Generator comprehensions vs explicit loops readability
**Learning:** Replacing concise generator comprehensions like `sum(1 for kw in list if kw in text)` with explicit, verbose `for` loops does yield minor execution speedups but heavily sacrifices readability. The prompt explicitly prohibits micro-optimizations that harm code readability.
**Action:** Avoid unrolling simple comprehensions or generator expressions into explicit loops merely for micro-optimization if it makes the code significantly more verbose and less pythonic.
