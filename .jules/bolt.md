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
## 2024-04-18 - Avoid string slicing in JSON raw_decode
**Learning:** While iterating through raw text to extract JSON chunks with `json.JSONDecoder().raw_decode()`, using string slicing (`s[start:]`) forces Python to copy memory redundantly, creating an O(N²) memory performance bottleneck when working with large outputs.
**Action:** Use `decoder.raw_decode(s, start)` instead of `s[start:]` to search through the string without allocating new copies. Additionally, be aware that when the `idx` parameter is used, `raw_decode` returns the absolute ending index in the original string (so use `start = index`), whereas without `idx`, it returns the relative index (which requires `start += index`).
