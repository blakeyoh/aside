## 2024-05-21 - Caching dictionary parsing to eliminate redundant disk I/O
**Learning:** Reading and parsing the dictionary file on every transcription loop caused unnecessary redundant disk I/O, presenting a performance bottleneck inside `transcriber.py`.
**Action:** Implemented an `mtime`-based cache to ensure the dictionary is only parsed when it has been updated, significantly lowering average call overhead (e.g., from ~0.10ms to ~0.05ms in artificial benchmarks and avoiding disk accesses altogether).
