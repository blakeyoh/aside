## 2025-03-05
**Optimization:** Bypassed `apply_replacements` dictionary iteration overhead
**💡 What:** We updated `Transcriber.__init__` to pre-compile default replacement rules, and modified the transcription pipeline to maintain a cached `list[tuple[re.Pattern, str]]` containing both user and default rules. This cached list is safely updated only when the `id(dict_data)` changes.
**🎯 Why:** Calling `apply_replacements` with a `dict` forces the function to iterate over its items and invoke an `lru_cache` lookup on `_get_compiled_pattern` for every single transcription, which created measurable overhead.
**📊 Impact:** Approximately ~15% faster execution for the post-processing replacements stage under typical default rule scenarios.
**🔬 Measurement:** Using Python's `time.perf_counter()` over 100,000 iterations, the overhead was reduced from ~1.94s to ~1.65s (baseline config) due to dropping the nested dictionary iterations and `isinstance(rules, dict)` checks on every pipeline step.
