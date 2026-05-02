
## 2024-05-18 - Caching Dictionary Parsing in Transcription Hot Path
**Learning:** Naively caching an object modified across threads (like `_cached_dict_data` between the UI setting it to `None` and the transcriber reading it) can lead to a crash due to race conditions during the transcription loop. Additionally, caching a file in-memory without checking its modified time (`mtime`) breaks hot-reloading for users who manually edit the file.
**Action:** When caching objects loaded from disk, use `os.path.getmtime` to maintain hot-reload capabilities. Assign the cached object to a local variable (`dict_data = self._cached_dict_data`) before operating on it to ensure thread safety against background cache invalidation.
