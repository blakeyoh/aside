## 2024-05-18 - Dictionary Modifications
**Learning:** Do not make any code changes to the dictionary or dictionary-related logic (e.g., parsing, caching, replacements).
**Action:** Always treat the dictionary logic as a high-risk area and avoid modifying it. Ensure future performance optimizations focus entirely on other systems.

## 2024-05-18 - Caching Hotkey Parsing
**Learning:** Reparsing the config for hotkeys (`parse_hotkey` strings to modifier integers/keycodes) within the `_on_hotkey_event` listener results in redundant calculations running on every single hotkey tap event.
**Action:** Extract the parsing step and use `@functools.lru_cache` to cache the string-to-keycode lookups, avoiding unneeded CPU overhead in a high-frequency polling loop.
