## 2024-05-01 - Cache parse_dictionary in Transcriber
**Learning:** `parse_dictionary` reads from disk every time `transcribe` is called. It shouldn't be read from disk on every single transcription loop, which blocks the whole thread.
**Action:** Implement caching for `parse_dictionary` by loading the dictionary once and then using it, and adding `reload_dictionary` logic.
