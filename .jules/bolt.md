## 2024-05-31 - [Parser String Concatenation Bottleneck]
**Learning:** O(N) string concatenation inside iterative text processing loops (`"".join(parts)[-1]`) becomes an O(N^2) hidden bottleneck when processing long streams of text like transcriptions.
**Action:** When extracting or checking boundary characters from lists of strings, use a backward iteration helper (e.g., `_get_last_char(parts)`) to access the rightmost non-empty string character in O(1) time without allocating intermediate full-text strings.
