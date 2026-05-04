## 2026-05-02 - Dynamic button states with CTkEntry
**Learning:** In customtkinter, using `StringVar.trace` for dynamic button updates can be problematic. A robust alternative is binding to the `<KeyRelease>` event of the `CTkEntry` directly.
**Action:** Use `<KeyRelease>` events to trigger callbacks that check `CTkEntry.get().strip()` to determine and set button states dynamically.
## 2026-05-02 - Seamless keyboard navigation for continuous data entry
**Learning:** For continuous data entry forms with paired inputs in customtkinter, users lose focus after `<Return>` submission or pressing `<Return>` in the first input fails.
**Action:** Use `.focus()` to manually route focus from the first field to the next upon `<Return>`, and route focus back to the primary input field upon successful submission, creating a seamless keyboard-only UX.
