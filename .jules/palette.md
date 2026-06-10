
## 2026-06-10 - Consistent dividers and button states
**Learning:** Avoid mixing native `tk.Frame` and `ctk.CTkFrame` components to prevent rendering and scaling inconsistencies. Additionally, `CTkButton` and `CTkOptionMenu` text color remains static on hover. To maintain readability on secondary elements with dark backgrounds (`BG2`) and light text, use a dark shade like `SEP` for `hover_color` and `dropdown_hover_color` instead of bright accent colors.
**Action:** For UI dividers, consistently use `ctk.CTkFrame(parent, fg_color=SEP, height=1, corner_radius=0)`. For secondary buttons and dropdowns with dark backgrounds, set `hover_color` and `dropdown_hover_color` to `SEP` to ensure optimal contrast and consistent interaction design.
