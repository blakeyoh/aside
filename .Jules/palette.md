## 2026-05-02 - Dynamic button states with CTkEntry
**Learning:** In customtkinter, using `StringVar.trace` for dynamic button updates can be problematic. A robust alternative is binding to the `<KeyRelease>` event of the `CTkEntry` directly.
**Action:** Use `<KeyRelease>` events to trigger callbacks that check `CTkEntry.get().strip()` to determine and set button states dynamically.

## 2026-05-02 - Seamless keyboard navigation for continuous data entry
**Learning:** For continuous data entry forms with paired inputs in customtkinter, users lose focus after `<Return>` submission or pressing `<Return>` in the first input fails.
**Action:** Use `.focus()` to manually route focus from the first field to the next upon `<Return>`, and route focus back to the primary input field upon successful submission, creating a seamless keyboard-only UX.

## 2026-05-03 - Focus management on continuous input forms
**Learning:** Seamless keyboard navigation for paired inputs (like key-value dictionary entries) and automatic re-focusing on inputs after submission makes repetitive data entry significantly smoother. Before this change, adding a dictionary rule required clicking the input again after each entry.
**Action:** When creating text input fields that users will likely use repeatedly in succession, always manage focus explicitly. For paired entries, hitting 'Return' in the first field should focus the second field; hitting 'Return' in the second field should submit the action and focus the first field again.

## 2026-05-18 - Native tk.Frame and CTkFrame mix
**Learning:** Mixing native `tk.Frame` and `ctk.CTkFrame` components can lead to rendering and scaling inconsistencies. For instance, using `tk.Frame` for UI dividers in a customTkinter app.
**Action:** Consistently use `ctk.CTkFrame(parent, fg_color=SEP, height=1, corner_radius=0)` for UI dividers to maintain aesthetic cohesion.

## 2026-05-18 - Hover color readability on secondary elements
**Learning:** Using bright accent colors (like `ACCENT`) for `hover_color` on secondary elements with dark backgrounds (`BG2`) and light text can result in poor contrast and a harsh aesthetic feel.
**Action:** Use a dark shade like `SEP` for `hover_color`, `button_hover_color`, and `dropdown_hover_color` on secondary elements to ensure text readability remains high and transitions are visually smoother.
