## 2026-05-02 - Dynamic button states with CTkEntry
**Learning:** In customtkinter, using `StringVar.trace` for dynamic button updates can be problematic. A robust alternative is binding to the `<KeyRelease>` event of the `CTkEntry` directly.
**Action:** Use `<KeyRelease>` events to trigger callbacks that check `CTkEntry.get().strip()` to determine and set button states dynamically.
