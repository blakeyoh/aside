## 2024-06-21 - [Fix O(N^2) string concatenation in parser]
**Learning:** Checking string boundaries in text processing loops using `"".join(parts)[-1]` becomes an O(N^2) bottleneck as the number of string segments grows, significantly degrading performance on long text accumulations.
**Action:** Always avoid `"".join()` inside loops. Instead, use a backward iteration helper like `_get_last_char(parts)` to find boundary characters in O(1) time without allocating large intermediate strings.
