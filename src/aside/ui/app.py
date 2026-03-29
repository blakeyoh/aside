"""Aside — main application shell.

Wires together: config -> HotkeyManager -> AudioCapture -> Transcriber -> UI.
Menu-bar-resident app: starts withdrawn, only shows on "Settings..." click.
"""

import fcntl
import logging
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

try:
    from PIL import Image as PILImage
    _PIL = True
except ImportError:
    _PIL = False

from Quartz import kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged

from aside.config import (
    load_config, save_config, DICTIONARY_FILE, CONFIG_DIR,
)
from aside.dictionary.hotwords import parse_dictionary, MAX_TERMS, ARROW
from aside.engine.audio import AudioCapture
from aside.engine.hotkeys import HotkeyManager, parse_hotkey, ACCESSIBILITY_ERROR
from aside.engine.transcriber import Transcriber
from aside.ui.menubar import MenuBar, APPKIT_AVAILABLE, hotkey_display, play_sound
from aside.ui.settings import build_settings
from aside.ui.theme import (
    BG, BG2, FG, FG2, ACCENT, SEP, FONT, MONO, POLL_MS, STATUS_MAP,
)

logger = logging.getLogger(__name__)

LOCK_FILE = CONFIG_DIR / "aside.lock"

_lock_fh = None  # keep file handle alive for the process lifetime

# Import for NSApplication only when available
if APPKIT_AVAILABLE:
    from AppKit import NSApplication, NSAlert


# -- Single-instance lock -----------------------------------------------------

def acquire_instance_lock() -> bool:
    """Acquire an exclusive lock. Returns True if this is the only instance."""
    global _lock_fh
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _lock_fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        _lock_fh.close()
        return False


# -- App ----------------------------------------------------------------------

class App(ctk.CTk):
    """Main Aside application window.

    Quiet launch: starts withdrawn (no window). The menu bar icon provides
    access to Settings and Quit. The window only appears on "Settings..." click.

    Event flow:
        HotkeyManager -> on_event -> _process_event (main thread via poll)
        _process_event -> starts/stops AudioCapture
        AudioCapture.stop() -> hands audio to Transcriber (background thread)
        Transcriber callbacks -> update UI via self.after(0, ...)
    """

    def __init__(self):
        ctk.set_appearance_mode("dark")           # MUST precede super().__init__()
        ctk.set_default_color_theme("dark-blue")  # MUST precede super().__init__()
        super().__init__()
        self.withdraw()                            # Quiet launch — starts hidden
        self.title("Aside")
        self.resizable(False, False)
        self.geometry("480x680")

        # -- State -------------------------------------------------------------
        self._cfg = load_config()
        self._capturing_hotkey = False
        self._capturing_toggle = False
        self._last_status = None
        self._recording = False
        self._trigger_held = False
        self._toggle_recording = False

        # -- Modules (initialized in after_idle) --------------------------------
        self._hotkeys: HotkeyManager | None = None
        self._audio = AudioCapture()
        self._transcriber: Transcriber | None = None
        self._menubar: MenuBar | None = None
        self._widgets: dict = {}

        self._build()

        # Hide on close — engine keeps running in background
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        # Defer heavy init until Tk's main loop is active
        self.after_idle(self._setup_menubar)
        self.after_idle(self._start_engine)

    # -- Public property for settings module -----------------------------------

    @property
    def cfg(self) -> dict:
        return self._cfg

    # -- Menu bar setup --------------------------------------------------------

    def _setup_menubar(self):
        icon_path = Path(__file__).resolve().parent.parent.parent.parent / "aside-logo.png"
        self._menubar = MenuBar(
            icon_path=icon_path,
            show_callback=self._show_window,
            quit_callback=self._quit,
        )

        if APPKIT_AVAILABLE:
            self.createcommand("::tk::mac::ReopenApplication", self._show_window)

    # -- Engine startup --------------------------------------------------------

    def _start_engine(self):
        self._transcriber = Transcriber(
            model_size=self._cfg["model_size"],
            language=self._cfg.get("language"),
            punctuation_config=self._cfg.get("punctuation"),
            on_status=self._on_status,
            on_transcription=self._on_transcription,
        )

        self._on_status("loading")
        threading.Thread(target=self._load_model_and_warmup, daemon=True).start()

        self._hotkeys = HotkeyManager(
            hotkey_config=self._cfg["hotkey"],
            toggle_hotkey_config=self._cfg.get("toggle_hotkey"),
            on_event=self._process_event,
            on_accessibility_error=lambda: self._on_status(ACCESSIBILITY_ERROR),
        )

        self._poll()

    def _load_model_and_warmup(self):
        """Load Whisper model then warm up PortAudio (background thread)."""
        if self._transcriber:
            self._transcriber.load_model()
        threading.Thread(target=AudioCapture.warmup, daemon=True).start()

    def _poll(self):
        """Drain the HotkeyManager's event queue on the main thread."""
        if self._hotkeys:
            self._hotkeys.poll()
        self.after(POLL_MS, self._poll)

    # -- Event processing (main thread) ----------------------------------------

    def _process_event(self, event_type: int, keycode: int, flags: int) -> None:
        """Handle keyboard events dispatched from HotkeyManager.poll()."""
        hk_mod, hk_key = parse_hotkey(self._cfg["hotkey"])
        toggle_cfg = self._cfg.get("toggle_hotkey")
        tg_mod, tg_key = parse_hotkey(toggle_cfg) if toggle_cfg else (0, -1)

        if event_type == kCGEventKeyDown:
            # Push-to-talk hotkey
            if (keycode == hk_key
                    and not self._trigger_held
                    and not self._toggle_recording):
                if (flags & hk_mod) == hk_mod:
                    self._trigger_held = True
                    self._start_recording()

            # Toggle (hands-free) hotkey
            elif (tg_key >= 0
                    and keycode == tg_key
                    and not self._trigger_held):
                if (flags & tg_mod) == tg_mod:
                    if not self._toggle_recording:
                        self._toggle_recording = True
                        self._start_recording()
                    else:
                        self._toggle_recording = False
                        self._stop_and_transcribe()

        elif event_type == kCGEventKeyUp:
            if keycode == hk_key and self._trigger_held:
                self._trigger_held = False
                self._stop_and_transcribe()

        elif event_type == kCGEventFlagsChanged:
            if self._trigger_held:
                if (flags & hk_mod) != hk_mod:
                    self._trigger_held = False
                    self._stop_and_transcribe()

    def _start_recording(self):
        if self._recording:
            return
        if not self._transcriber or not self._transcriber.model_loaded:
            return
        self._recording = True
        self._on_status("recording")
        if not self._audio.start():
            self._recording = False
            self._toggle_recording = False
            self._on_status("error: microphone unavailable")

    def _stop_and_transcribe(self):
        if not self._recording:
            return
        self._recording = False
        self._on_status("transcribing")
        # AudioCapture.stop() blocks (PortAudio drain) — run on background thread.
        # Transcriber.transcribe() also runs there.
        audio_ref = self._audio
        transcriber_ref = self._transcriber

        def _bg():
            audio = audio_ref.stop()
            if audio is not None and transcriber_ref is not None:
                transcriber_ref.transcribe(audio)
            elif transcriber_ref is not None:
                transcriber_ref._on_status("ready")

        threading.Thread(target=_bg, daemon=True).start()

    # -- Layout ----------------------------------------------------------------

    def _build(self):
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=BG, corner_radius=0,
            scrollbar_fg_color=BG2,
            scrollbar_button_color=SEP,
            scrollbar_button_hover_color=FG2,
        )
        self._body.pack(fill="both", expand=True)
        self._header_section()
        self._divider()
        self._preview_section()
        self._divider()
        self._instructions_section()
        self._divider()
        self._settings_section()

    def _divider(self):
        tk.Frame(self._body, bg=SEP, height=1).pack(fill="x")

    def _header_section(self):
        f = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        f.pack(fill="x", padx=24, pady=(20, 16))

        # Title row
        title_row = ctk.CTkFrame(f, fg_color="transparent", corner_radius=0)
        title_row.pack(anchor="w")

        if _PIL:
            try:
                icon_path = Path(__file__).resolve().parent.parent.parent.parent / "aside-logo.png"
                pil_img = PILImage.open(str(icon_path))
                self._header_icon = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(26, 26),
                )
                ctk.CTkLabel(
                    title_row, image=self._header_icon, text="",
                ).pack(side="left", padx=(0, 8))
            except Exception:
                pass

        ctk.CTkLabel(
            title_row, text="Aside",
            font=(FONT, 18, "bold"), text_color=FG,
        ).pack(side="left")

        ctk.CTkLabel(
            f,
            text=(
                "Aside is a private macOS speech-to-text utility that instantly "
                "transcribes your speech into any active text field. 100% local — "
                "your voice never leaves this Mac."
            ),
            font=(FONT, 12), text_color=FG2,
            wraplength=360, justify="left",
        ).pack(anchor="w", pady=(6, 0))

        row = ctk.CTkFrame(f, fg_color="transparent", corner_radius=0)
        row.pack(anchor="w", pady=(10, 0))

        self._dot = ctk.CTkLabel(row, text="\u25cf", font=(FONT, 14), text_color="#FF9F0A")
        self._dot.pack(side="left", padx=(0, 7))

        self._status_lbl = ctk.CTkLabel(
            row, text="Loading model\u2026", font=(FONT, 14), text_color=FG,
        )
        self._status_lbl.pack(side="left")

        # "Grant Access" button — shown only when Accessibility is missing
        self._grant_btn = ctk.CTkButton(
            f, text="Grant Access in System Settings",
            font=(FONT, 12), fg_color=ACCENT, text_color="#0A0A0A",
            hover_color="#00A8C0", corner_radius=6,
            command=self._open_accessibility_settings,
        )
        # Starts hidden — _on_status shows it via pack when needed

    def _preview_section(self):
        f = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        f.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(
            f, text="Last transcription", font=(FONT, 12), text_color=FG2,
        ).pack(anchor="w")

        self._preview = ctk.CTkLabel(
            f, text="\u2014",
            font=(MONO, 13), fg_color=BG2, text_color=FG,
            wraplength=360, justify="left",
            anchor="w", corner_radius=4,
            padx=12, pady=10,
        )
        self._preview.pack(fill="x", pady=(6, 0))

    def _instructions_section(self):
        f = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        f.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(
            f, text="How to use", font=(FONT, 12), text_color=FG2,
        ).pack(anchor="w", pady=(0, 8))

        hotkey = hotkey_display(self._cfg["hotkey"])
        steps = [
            "Click into any text field",
            f"Hold  {hotkey}",
            "Speak clearly into your microphone",
            "Release \u2014 text appears instantly",
        ]
        self._hotkey_step_lbl = None
        for i, step in enumerate(steps, 1):
            row = ctk.CTkFrame(f, fg_color="transparent", corner_radius=0)
            row.pack(anchor="w", pady=2)
            ctk.CTkLabel(
                row, text=str(i), font=(MONO, 12), width=28,
                fg_color=BG2, text_color=FG2, corner_radius=4,
            ).pack(side="left")
            lbl = ctk.CTkLabel(row, text=f"  {step}", font=(FONT, 13), text_color=FG)
            lbl.pack(side="left")
            if i == 2:
                self._hotkey_step_lbl = lbl

        # Toggle step — shown when toggle hotkey is configured
        self._toggle_step_row = ctk.CTkFrame(f, fg_color="transparent", corner_radius=0)
        ctk.CTkLabel(
            self._toggle_step_row, text="5", font=(MONO, 12), width=28,
            fg_color=BG2, text_color=FG2, corner_radius=4,
        ).pack(side="left")
        self._toggle_step_lbl = ctk.CTkLabel(
            self._toggle_step_row,
            text="  Hands-free: \u2026 starts & stops recording",
            font=(FONT, 13), text_color=FG,
        )
        self._toggle_step_lbl.pack(side="left")

        if self._cfg.get("toggle_hotkey"):
            display = hotkey_display(self._cfg["toggle_hotkey"])
            self._toggle_step_lbl.configure(
                text=f"  Hands-free: {display} starts & stops recording",
            )
            self._toggle_step_row.pack(anchor="w", pady=2)

    def _settings_section(self):
        f = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        f.pack(fill="x", padx=24, pady=16)

        self._widgets = build_settings(self, f)
        self._wire_settings()

    def _wire_settings(self):
        """Attach App callbacks to the settings panel widgets."""
        w = self._widgets

        # Hotkey buttons
        w["hotkey_btn"].configure(command=self._capture_hotkey)
        w["toggle_btn"].configure(command=self._capture_toggle)
        w["toggle_clear_btn"].configure(command=self._clear_toggle)

        # Dictionary buttons
        w["hw_add_btn"].configure(command=self._add_hotword)
        w["rep_add_btn"].configure(command=self._add_replacement)
        w["reload_btn"].configure(command=self._reload_dictionary)

        # Apply button
        w["apply_btn"].configure(command=self._apply_settings)

    # -- Hotkey capture --------------------------------------------------------

    def _capture_hotkey(self):
        if self._capturing_hotkey or not self._hotkeys:
            return
        self._capturing_hotkey = True
        self._widgets["hotkey_btn"].configure(
            text="Press combo\u2026", state="disabled", text_color=FG2,
        )
        self._hotkeys.start_capture(self._on_hotkey_captured)

    def _on_hotkey_captured(self, config: dict):
        """Called from poll() on the main thread — safe to update UI."""
        # If new push-to-talk conflicts with toggle, clear toggle
        if config == self._cfg.get("toggle_hotkey"):
            self._apply_toggle_hotkey(None)

        self._cfg = {**self._cfg, "hotkey": config}
        save_config(self._cfg)

        if self._hotkeys:
            self._hotkeys.update_hotkey(config)

        display = hotkey_display(config)
        self._widgets["hotkey_lbl"].configure(text=display)
        if self._hotkey_step_lbl:
            self._hotkey_step_lbl.configure(text=f"  Hold  {display}")

        self._widgets["hotkey_btn"].configure(
            text="Change", state="normal", text_color=FG,
        )
        self._capturing_hotkey = False

    # -- Toggle hotkey capture -------------------------------------------------

    def _capture_toggle(self):
        if self._capturing_toggle or self._capturing_hotkey or not self._hotkeys:
            return
        self._capturing_toggle = True
        self._widgets["toggle_btn"].configure(
            text="Press combo\u2026", state="disabled", text_color=FG2,
        )
        self._hotkeys.start_capture(self._on_toggle_captured)

    def _on_toggle_captured(self, config: dict):
        """Called from poll() on the main thread — safe to update UI."""
        # Conflict with push-to-talk — silently reject
        if config == self._cfg["hotkey"]:
            self._widgets["toggle_btn"].configure(
                text="Set", state="normal", text_color=FG,
            )
            self._capturing_toggle = False
            return

        self._apply_toggle_hotkey(config)
        self._widgets["toggle_btn"].configure(
            text="Change", state="normal", text_color=FG,
        )
        self._capturing_toggle = False

    def _clear_toggle(self):
        self._apply_toggle_hotkey(None)

    def _apply_toggle_hotkey(self, config: dict | None):
        """Update toggle hotkey in config, engine, and UI."""
        self._cfg = {**self._cfg, "toggle_hotkey": config}
        save_config(self._cfg)
        self._toggle_recording = False

        if self._hotkeys:
            self._hotkeys.update_toggle_hotkey(config)

        if config:
            display = hotkey_display(config)
            self._widgets["toggle_lbl"].configure(text=display)
            self._widgets["toggle_btn"].configure(text="Change")
            self._widgets["toggle_clear_btn"].pack(side="right", padx=(4, 0))
            self._toggle_step_lbl.configure(
                text=f"  Hands-free: {display} starts & stops recording",
            )
            self._toggle_step_row.pack(anchor="w", pady=2)
        else:
            self._widgets["toggle_lbl"].configure(text="\u2014")
            self._widgets["toggle_btn"].configure(text="Set")
            self._widgets["toggle_clear_btn"].pack_forget()
            self._toggle_step_row.pack_forget()

    # -- Dictionary handlers ---------------------------------------------------

    def _add_hotword(self):
        term = self._widgets["hw_entry"].get().strip()
        if not self._validate_dict_add(term):
            return

        self._append_to_dictionary(term)
        self._widgets["hw_entry"].delete(0, "end")
        self._refresh_term_count()

    def _add_replacement(self):
        wrong = self._widgets["rep_wrong"].get().strip()
        right = self._widgets["rep_right"].get().strip()
        if not wrong or not right:
            return
        line = f"{wrong} {ARROW} {right}"
        if not self._validate_dict_add(line, check_key=wrong):
            return

        self._append_to_dictionary(line)
        self._widgets["rep_wrong"].delete(0, "end")
        self._widgets["rep_right"].delete(0, "end")
        self._refresh_term_count()

    def _validate_dict_add(self, term: str, check_key: str | None = None) -> bool:
        """Validate: non-empty, under cap, no duplicate."""
        if not term:
            return False
        dict_data = parse_dictionary(DICTIONARY_FILE)
        if dict_data.term_count >= MAX_TERMS:
            return False
        # Check for duplicates
        key = check_key or term
        existing_hotwords = set(dict_data.hotwords)
        existing_replacements = set(dict_data.replacements.keys())
        if key in existing_hotwords or key in existing_replacements:
            return False
        return True

    def _append_to_dictionary(self, line: str):
        """Append a line to the dictionary file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(DICTIONARY_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n{line}")
        except OSError as exc:
            logger.error("Failed to append to dictionary: %s", exc)

    def _refresh_term_count(self):
        dict_data = parse_dictionary(DICTIONARY_FILE)
        self._widgets["term_count_lbl"].configure(
            text=f"{dict_data.term_count} / {MAX_TERMS} terms",
        )

    def _reload_dictionary(self):
        """Reload dictionary display (after external edit)."""
        self._refresh_term_count()
        if self._transcriber:
            self._transcriber.reload_dictionary()

    # -- Apply settings --------------------------------------------------------

    def _apply_settings(self):
        """Save all settings and reload model/language/punctuation."""
        w = self._widgets
        model_size = w["model_var"].get()
        lang_name = w["lang_var"].get()
        lang_code = w["lang_codes"].get(lang_name)

        punct_config = {
            "capitalization": w["cap_var"].get(),
            "smart_quotes": w["sq_var"].get(),
            "trailing_space": w["ts_var"].get(),
        }

        self._cfg = {
            **self._cfg,
            "model_size": model_size,
            "language": lang_code,
            "punctuation": punct_config,
        }
        save_config(self._cfg)

        if self._transcriber:
            # Reload model if size changed
            if model_size != self._transcriber.model_size:
                self._transcriber.reload_model(model_size)
            # Update language and punctuation immediately
            self._transcriber.update_language(lang_code)
            self._transcriber.update_punctuation(punct_config)

    # -- Status callbacks ------------------------------------------------------

    def _on_status(self, status: str):
        is_accessibility_error = (status == ACCESSIBILITY_ERROR)
        if status.startswith("error"):
            color = "#FF453A"
            label = "Accessibility access needed" if is_accessibility_error else status
        else:
            key = status if status in STATUS_MAP else "ready"
            color, label = STATUS_MAP[key]

        play_start = status == "recording"

        def _update():
            play_done = status == "ready" and self._last_status == "transcribing"
            self._last_status = status
            self._dot.configure(text_color=color)
            self._status_lbl.configure(text=label)

            if is_accessibility_error:
                self._grant_btn.pack(anchor="w", pady=(8, 0))
            else:
                self._grant_btn.pack_forget()

            # Menu bar icon: amber circle when recording, idle otherwise
            if self._menubar:
                self._menubar.set_recording(status == "recording")

            if play_start:
                play_sound("Tink")
            elif play_done:
                play_sound("Pop")

        self.after(0, _update)

    def _on_transcription(self, text: str):
        preview = text[:140] + ("\u2026" if len(text) > 140 else "")
        self.after(0, lambda: self._preview.configure(text=preview))

    # -- Window management -----------------------------------------------------

    def _show_window(self):
        self._center()
        self.deiconify()
        self.lift()
        self.focus_force()
        if APPKIT_AVAILABLE:
            try:
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception:
                pass

    def _center(self):
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _open_accessibility_settings(self):
        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security"
             "?Privacy_Accessibility"],
            check=False,
        )

    def _quit(self):
        if self._hotkeys:
            self._hotkeys.shutdown()
        if self._audio and self._audio.is_recording:
            # Stop on background thread — stop() blocks
            threading.Thread(
                target=self._audio.stop, daemon=True,
            ).start()
        self.destroy()


# -- Entry point ---------------------------------------------------------------

def main():
    if not acquire_instance_lock():
        if APPKIT_AVAILABLE:
            try:
                alert = NSAlert.alloc().init()
                alert.setMessageText_("Aside is already running")
                alert.setInformativeText_("Check the menu bar for the icon.")
                alert.runModal()
            except Exception:
                pass
        sys.exit(0)

    App().mainloop()
