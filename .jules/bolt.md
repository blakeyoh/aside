## 2024-06-28 - Optimize array joining in text processing loops
**Learning:** Checking string boundaries by continually joining string arrays via `"".join(parts)[-1]` within a processing loop leads to an O(N^2) overhead for long text inputs.
**Action:** Use a backward iteration helper `_get_last_char(parts)` to find the rightmost non-empty string character in O(1) time without allocating and copying the entire concatenated string.
