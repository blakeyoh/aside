## 2024-05-18 - Caching Dictionary Disk I/O
**Learning:** Reparsing dictionary files (`parse_dictionary`) on the main transcription hot path (every audio slice) creates unnecessary continuous disk I/O and CPU overhead for regex compilations.
**Action:** Use an in-memory cache tied to `os.path.getmtime` to lazily invalidate and reparse files only when they actually change. Ensure the cached object is assigned to a local variable for thread safety before operations.
