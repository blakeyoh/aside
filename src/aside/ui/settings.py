"""Settings panel for Aside.

Sections: Model, Hotkey, Toggle Hotkey, Dictionary, Language, Punctuation.
"""

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk
from AppKit import NSWorkspace
from Foundation import NSURL

from aside.config import DICTIONARY_FILE, ensure_dictionary_file
from aside.dictionary.hotwords import parse_dictionary, MAX_TERMS
from aside.ui.menubar import hotkey_display
from aside.ui.theme import (
    BG2,
    FG,
    FG2,
    ACCENT,
    SEP,
    FONT,
    MONO,
    MODELS,
    MODEL_LABELS,
    LANGUAGES,
)

if TYPE_CHECKING:
    from aside.ui.app import App


def open_dictionary_file() -> None:
    """Open the custom dictionary in the user's default editor."""
    ensure_dictionary_file()
    url = NSURL.fileURLWithPath_(str(DICTIONARY_FILE))
    NSWorkspace.sharedWorkspace().openURL_(url)


def build_settings(parent: "App", frame: ctk.CTkFrame) -> dict:
    """Build the settings panel and return widget references.

    Returns a dict of widgets the App needs to update dynamically.
    """
    widgets = {}
    cfg = parent.cfg

    ctk.CTkLabel(frame, text="Settings", font=(FONT, 12), text_color=FG2).pack(
        anchor="w", pady=(0, 10)
    )

    # ── Model ──────────────────────────────────────────────────────────────
    model_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    model_row.pack(fill="x")
    ctk.CTkLabel(model_row, text="Model", font=(FONT, 14), text_color=FG).pack(
        side="left"
    )

    model_var = tk.StringVar(value=cfg["model_size"])
    widgets["model_var"] = model_var

    model_hint = ctk.CTkLabel(
        frame,
        text=MODEL_LABELS[cfg["model_size"]],
        font=(FONT, 12),
        text_color=FG2,
    )

    dropdown = ctk.CTkOptionMenu(
        model_row,
        variable=model_var,
        values=MODELS,
        command=lambda val: model_hint.configure(text=MODEL_LABELS.get(val, "")),
        fg_color=BG2,
        text_color=FG,
        button_color=ACCENT,
        button_hover_color="#00A8C0",
        dropdown_fg_color=BG2,
        dropdown_text_color=FG,
        dropdown_hover_color=SEP,
        font=(FONT, 13),
        width=240,
    )
    dropdown.pack(side="right")
    model_hint.pack(anchor="w", pady=(6, 0))
    widgets["model_hint"] = model_hint

    _divider(frame)

    # ── Language ───────────────────────────────────────────────────────────
    lang_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    lang_row.pack(fill="x", pady=(10, 0))
    ctk.CTkLabel(lang_row, text="Language", font=(FONT, 14), text_color=FG).pack(
        side="left"
    )

    lang_names = [name for name, _ in LANGUAGES]
    lang_codes = {name: code for name, code in LANGUAGES}
    current_lang = cfg.get("language")
    current_name = next((n for n, c in LANGUAGES if c == current_lang), "Auto-detect")

    lang_var = tk.StringVar(value=current_name)
    widgets["lang_var"] = lang_var
    widgets["lang_codes"] = lang_codes

    ctk.CTkOptionMenu(
        lang_row,
        variable=lang_var,
        values=lang_names,
        fg_color=BG2,
        text_color=FG,
        button_color=ACCENT,
        button_hover_color="#00A8C0",
        dropdown_fg_color=BG2,
        dropdown_text_color=FG,
        dropdown_hover_color=SEP,
        font=(FONT, 13),
        width=200,
    ).pack(side="right")

    _divider(frame)

    # ── Hotkey ─────────────────────────────────────────────────────────────
    hotkey_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    hotkey_row.pack(fill="x", pady=(10, 0))
    ctk.CTkLabel(hotkey_row, text="Hotkey", font=(FONT, 14), text_color=FG).pack(
        side="left"
    )

    hotkey_lbl = ctk.CTkLabel(
        hotkey_row,
        text=hotkey_display(cfg["hotkey"]),
        font=(MONO, 13),
        fg_color=BG2,
        text_color=FG,
        padx=8,
        pady=3,
        corner_radius=4,
    )
    hotkey_lbl.pack(side="right", padx=(8, 0))
    widgets["hotkey_lbl"] = hotkey_lbl

    hotkey_btn = ctk.CTkButton(
        hotkey_row,
        text="Change",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
    )
    hotkey_btn.pack(side="right")
    widgets["hotkey_btn"] = hotkey_btn

    hotkey_cancel_btn = ctk.CTkButton(
        hotkey_row,
        text="Cancel",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG2,
        hover_color=SEP,
        corner_radius=6,
    )
    widgets["hotkey_cancel_btn"] = hotkey_cancel_btn

    # ── Toggle Hotkey ──────────────────────────────────────────────────────
    toggle_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    toggle_row.pack(fill="x", pady=(10, 0))
    ctk.CTkLabel(toggle_row, text="Toggle Hotkey", font=(FONT, 14), text_color=FG).pack(
        side="left"
    )

    toggle_cfg = cfg.get("toggle_hotkey")
    toggle_lbl = ctk.CTkLabel(
        toggle_row,
        text=hotkey_display(toggle_cfg) if toggle_cfg else "\u2014",
        font=(MONO, 13),
        fg_color=BG2,
        text_color=FG,
        padx=8,
        pady=3,
        corner_radius=4,
    )
    toggle_lbl.pack(side="right", padx=(8, 0))
    widgets["toggle_lbl"] = toggle_lbl

    toggle_clear_btn = ctk.CTkButton(
        toggle_row,
        text="Clear",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG2,
        hover_color=SEP,
        corner_radius=6,
    )
    if toggle_cfg:
        toggle_clear_btn.pack(side="right", padx=(4, 0))
    widgets["toggle_clear_btn"] = toggle_clear_btn

    toggle_btn = ctk.CTkButton(
        toggle_row,
        text="Set",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
    )
    toggle_btn.pack(side="right")
    widgets["toggle_btn"] = toggle_btn

    toggle_cancel_btn = ctk.CTkButton(
        toggle_row,
        text="Cancel",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG2,
        hover_color=SEP,
        corner_radius=6,
    )
    widgets["toggle_cancel_btn"] = toggle_cancel_btn

    _divider(frame)

    # ── Dictionary ─────────────────────────────────────────────────────────
    dict_section = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    dict_section.pack(fill="x", pady=(10, 0))

    dict_header = ctk.CTkFrame(dict_section, fg_color="transparent", corner_radius=0)
    dict_header.pack(fill="x")
    ctk.CTkLabel(
        dict_header, text="Custom Dictionary", font=(FONT, 14), text_color=FG
    ).pack(side="left")

    ensure_dictionary_file()
    dict_data = parse_dictionary(DICTIONARY_FILE)
    term_count_lbl = ctk.CTkLabel(
        dict_header,
        text=f"{dict_data.term_count} / {MAX_TERMS} terms",
        font=(FONT, 12),
        text_color=FG2,
    )
    term_count_lbl.pack(side="right")
    widgets["term_count_lbl"] = term_count_lbl

    # Add Hotword row
    hw_row = ctk.CTkFrame(dict_section, fg_color="transparent", corner_radius=0)
    hw_row.pack(fill="x", pady=(8, 0))
    ctk.CTkLabel(hw_row, text="Add Hotword", font=(FONT, 11), text_color=FG2).pack(
        anchor="w"
    )

    hw_input_row = ctk.CTkFrame(hw_row, fg_color="transparent", corner_radius=0)
    hw_input_row.pack(fill="x", pady=(2, 0))
    hw_entry = ctk.CTkEntry(
        hw_input_row, placeholder_text="e.g. HIPAA", font=(FONT, 13)
    )
    hw_entry.pack(side="left", fill="x", expand=True)

    hw_add_btn = ctk.CTkButton(
        hw_input_row,
        text="Add",
        width=60,
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
        state="disabled",
    )
    hw_add_btn.pack(side="right", padx=(8, 0))
    widgets["hw_entry"] = hw_entry
    widgets["hw_add_btn"] = hw_add_btn

    # Add Replacement row
    rep_row = ctk.CTkFrame(dict_section, fg_color="transparent", corner_radius=0)
    rep_row.pack(fill="x", pady=(8, 0))
    ctk.CTkLabel(rep_row, text="Add Replacement", font=(FONT, 11), text_color=FG2).pack(
        anchor="w"
    )

    rep_input_row = ctk.CTkFrame(rep_row, fg_color="transparent", corner_radius=0)
    rep_input_row.pack(fill="x", pady=(2, 0))
    rep_wrong = ctk.CTkEntry(
        rep_input_row, placeholder_text="wrong", font=(FONT, 13), width=120
    )
    rep_wrong.pack(side="left")
    ctk.CTkLabel(rep_input_row, text="\u2192", font=(FONT, 13), text_color=FG2).pack(
        side="left", padx=4
    )
    rep_right = ctk.CTkEntry(
        rep_input_row, placeholder_text="right", font=(FONT, 13), width=120
    )
    rep_right.pack(side="left")

    rep_add_btn = ctk.CTkButton(
        rep_input_row,
        text="Add",
        width=60,
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
        state="disabled",
    )
    rep_add_btn.pack(side="right", padx=(8, 0))
    widgets["rep_wrong"] = rep_wrong
    widgets["rep_right"] = rep_right
    widgets["rep_add_btn"] = rep_add_btn

    # Dict action buttons
    dict_btn_row = ctk.CTkFrame(dict_section, fg_color="transparent", corner_radius=0)
    dict_btn_row.pack(fill="x", pady=(8, 0))

    edit_btn = ctk.CTkButton(
        dict_btn_row,
        text="Edit Dictionary",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
        command=open_dictionary_file,
    )
    edit_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

    reload_btn = ctk.CTkButton(
        dict_btn_row,
        text="Reload",
        font=(FONT, 12),
        fg_color=BG2,
        text_color=FG,
        hover_color=SEP,
        corner_radius=6,
    )
    reload_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
    widgets["reload_btn"] = reload_btn

    _divider(frame)

    # ── Punctuation ────────────────────────────────────────────────────────
    punct_section = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    punct_section.pack(fill="x", pady=(10, 0))
    ctk.CTkLabel(
        punct_section, text="Punctuation", font=(FONT, 14), text_color=FG
    ).pack(anchor="w")

    punct_cfg = cfg.get("punctuation", {})

    # Capitalization
    cap_row = ctk.CTkFrame(punct_section, fg_color="transparent", corner_radius=0)
    cap_row.pack(fill="x", pady=(6, 0))
    ctk.CTkLabel(cap_row, text="Capitalization", font=(FONT, 12), text_color=FG2).pack(
        side="left"
    )
    cap_var = tk.StringVar(value=punct_cfg.get("capitalization", "sentence"))
    ctk.CTkOptionMenu(
        cap_row,
        variable=cap_var,
        values=["sentence", "as-spoken", "off"],
        fg_color=BG2,
        text_color=FG,
        button_color=ACCENT,
        font=(FONT, 12),
        width=140,
    ).pack(side="right")
    widgets["cap_var"] = cap_var

    # Smart quotes
    sq_var = tk.BooleanVar(value=punct_cfg.get("smart_quotes", False))
    ctk.CTkCheckBox(
        punct_section,
        text="Smart quotes",
        variable=sq_var,
        font=(FONT, 12),
        text_color=FG2,
        fg_color=ACCENT,
        hover_color="#00A8C0",
    ).pack(anchor="w", pady=(6, 0))
    widgets["sq_var"] = sq_var

    # Trailing space
    ts_var = tk.BooleanVar(value=punct_cfg.get("trailing_space", True))
    ctk.CTkCheckBox(
        punct_section,
        text="Space after punctuation",
        variable=ts_var,
        font=(FONT, 12),
        text_color=FG2,
        fg_color=ACCENT,
        hover_color="#00A8C0",
    ).pack(anchor="w", pady=(2, 0))
    widgets["ts_var"] = ts_var

    # ── Footer ─────────────────────────────────────────────────────────────
    ctk.CTkLabel(
        frame,
        text="Audio is processed locally \u2014 your voice never leaves this Mac.",
        font=(FONT, 12),
        text_color=FG2,
        wraplength=360,
        justify="left",
    ).pack(anchor="w", pady=(14, 0))

    apply_btn = ctk.CTkButton(
        frame,
        text="Apply",
        font=(FONT, 13),
        fg_color=ACCENT,
        text_color="#0A0A0A",
        hover_color="#00A8C0",
        corner_radius=8,
    )
    apply_btn.pack(anchor="e", pady=(12, 4))
    widgets["apply_btn"] = apply_btn

    return widgets


def _divider(parent):
    tk.Frame(parent, bg=SEP, height=1).pack(fill="x", pady=(10, 0))
