## 2026-05-02 - Dynamic button states with CTkEntry
**Learning:** In customtkinter, using `StringVar.trace` for dynamic button updates can be problematic. A robust alternative is binding to the `<KeyRelease>` event of the `CTkEntry` directly.
**Action:** Use `<KeyRelease>` events to trigger callbacks that check `CTkEntry.get().strip()` to determine and set button states dynamically.

## 2026-05-02 - Seamless keyboard navigation for continuous data entry
**Learning:** For continuous data entry forms with paired inputs in customtkinter, users lose focus after `<Return>` submission or pressing `<Return>` in the first input fails.
**Action:** Use `.focus()` to manually route focus from the first field to the next upon `<Return>`, and route focus back to the primary input field upon successful submission, creating a seamless keyboard-only UX.

## 2026-05-03 - Focus management on continuous input forms
**Learning:** Seamless keyboard navigation for paired inputs (like key-value dictionary entries) and automatic re-focusing on inputs after submission makes repetitive data entry significantly smoother. Before this change, adding a dictionary rule required clicking the input again after each entry.
**Action:** When creating text input fields that users will likely use repeatedly in succession, always manage focus explicitly. For paired entries, hitting 'Return' in the first field should focus the second field; hitting 'Return' in the second field should submit the action and focus the first field again.

## 2026-06-03 - CTkButton Hover Color Contrast
**Learning:** In customtkinter, `CTkButton` text color remains static on hover. Using a bright accent or red color for `hover_color` on secondary buttons with `fg_color=BG2` (dark) and `text_color=FG` (white) or `FG2` (gray) causes severe contrast issues and unreadable text during hover states.
**Action:** For secondary buttons with dark backgrounds (`BG2`), consistently use `hover_color=SEP` (a slightly lighter dark shade) instead of bright accents to maintain readable text contrast. Apply this same pattern to `dropdown_hover_color` in `CTkOptionMenu`.

## 2026-06-03 - Consistent UI Components
**Learning:** The settings UI was using native `tk.Frame` for dividers, while onboarding used `ctk.CTkFrame`. Mixing native Tk and CustomTkinter components can cause scaling and theme rendering inconsistencies.
**Action:** Systematically replace native `tk.Frame` dividers with `ctk.CTkFrame(..., fg_color=SEP, height=1, corner_radius=0)` for uniform visual rendering.
