"""Main application shell for Aside.

Wires together the UI (customtkinter + AppKit menu bar), the hotkey manager,
audio capture, and the Whisper transcription pipeline. Manages state machine
transitions between loading → ready → recording → transcribing.

Threading model:
  Main thread (Tk): UI updates, hotkey polling, state transitions
  Background "event-tap": CGEventTap CFRunLoop (via HotkeyManager)
  Background "model-load" / "transcribe": Whisper model + pipeline
"""
import fcntl
import logging
import os
import sys
import threading

import customtkinter as ctk

from aside import __version__
from aside.config import (
    CONFIG_DIR,
    DICTIONARY_FILE,
    load_config,
    save_config,
    ensure_dictionary_file,
)
from aside.dictionary.hotwords import parse_dictionary, MAX_TERMS
from aside.engine.audio import AudioCapture
from aside.engine.hotkeys import HotkeyManager, hotkeys_equal, parse_hotkey
from aside.engine.transcriber import Transcriber
from aside.resources import resource_path
from aside.ui.menubar import MenuBar, hotkey_display, play_sound
from aside.ui.settings import build_settings
from aside.ui.theme import BG, FG, FG2, FONT, ACCENT, POLL_MS, STATUS_MAP

logger = logging.getLogger(__name__)

ICON_PATH = resource_path("aside-logo.png")
LOCK_FILE = CONFIG_DIR / "aside.lock"


def _acquire_lock():
    """Single-instance lock via fcntl.flock(). Returns lock fd or None."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = open(LOCK_FILE, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        return None


# ── customtkinter appearance must be set BEFORE CTk.__init__() ───────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    """Main Aside application window."""

    def __init__(self):
        # Single-instance guard
        self._lock_fd = _acquire_lock()
        if self._lock_fd is None:
            try:
                from AppKit import NSAlert
                alert = NSAlert.alloc().init()
                alert.setMessageText_("Aside is already running")
                alert.setInformativeText_(
                    "Another instance of Aside is already active."
                )
                alert.runModal()
            except Exception:
                pass
            sys.exit(0)

        super().__init__()

        # ── Window setup (starts withdrawn) ──────────────────────────────
        self.title("Aside")
        self.geometry("420x640")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.withdraw()

        # ── Config ───────────────────────────────────────────────────────
        self.cfg = load_config()
        if hotkeys_equal(self.cfg.get("hotkey"), self.cfg.get("toggle_hotkey")):
            logger.warning("Toggle hotkey matched push-to-talk hotkey; disabling toggle")
            self.cfg["toggle_hotkey"] = None
            save_config(self.cfg)

        # ── State ────────────────────────────────────────────────────────
        self._state = "loading"  # loading → ready → recording → transcribing
        self._toggle_active = False  # toggle-hotkey recording mode
        self._hotkey_poll_failed = False

        # ── Status bar (top of window) ───────────────────────────────────
        status_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        status_frame.pack(fill="x", padx=16, pady=(12, 0))

        self._status_dot = ctk.CTkLabel(
            status_frame, text="●", font=(FONT, 14),
            text_color=STATUS_MAP["loading"][0],
        )
        self._status_dot.pack(side="left")

        self._status_label = ctk.CTkLabel(
            status_frame, text=STATUS_MAP["loading"][1],
            font=(FONT, 13), text_color=FG,
        )
        self._status_label.pack(side="left", padx=(6, 0))

        self._version_label = ctk.CTkLabel(
            status_frame, text=f"v{__version__}",
            font=(FONT, 11), text_color=FG2,
        )
        self._version_label.pack(side="right")

        # ── Settings panel (scrollable) ──────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=(10, 12))
        self._widgets = build_settings(self, scroll)

        # ── Wire settings button callbacks ───────────────────────────────
        self._widgets["apply_btn"].configure(command=self._on_apply)
        self._widgets["hotkey_btn"].configure(command=self._on_capture_hotkey)
        self._widgets["hotkey_cancel_btn"].configure(command=self._on_cancel_hotkey_capture)
        self._widgets["toggle_btn"].configure(command=self._on_capture_toggle)
        self._widgets["toggle_cancel_btn"].configure(command=self._on_cancel_hotkey_capture)
        self._widgets["toggle_clear_btn"].configure(command=self._on_clear_toggle)
        self._widgets["hw_add_btn"].configure(command=self._on_add_hotword)
        self._widgets["rep_add_btn"].configure(command=self._on_add_replacement)
        self._widgets["reload_btn"].configure(command=self._on_reload_dictionary)

        # ── Engine components ────────────────────────────────────────────
        self._audio = AudioCapture()
        self._transcriber = Transcriber(
            model_size=self.cfg["model_size"],
            language=self.cfg.get("language"),
            punctuation_config=self.cfg.get("punctuation"),
            on_status=self._on_engine_status,
            on_transcription=self._on_transcription,
        )

        # ── Hotkey manager ───────────────────────────────────────────────
        self._hotkeys = HotkeyManager(
            hotkey_config=self.cfg.get("hotkey"),
            toggle_hotkey_config=self.cfg.get("toggle_hotkey"),
            on_event=self._on_hotkey_event,
            on_accessibility_error=self._on_accessibility_error,
        )

        # ── Menu bar ────────────────────────────────────────────────────
        self._menubar = MenuBar(
            icon_path=ICON_PATH,
            show_callback=self._request_show_settings,
            quit_callback=self._on_quit,
        )

        # ── Window protocol ─────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        # ── Kick off engine ─────────────────────────────────────────────
        self.after_idle(self._start_engine)
        self._poll_job = self.after(POLL_MS, self._poll_hotkeys)
        if os.environ.get("ASIDE_SHOW_SETTINGS_ON_LAUNCH") == "1":
            self.after(300, self._show_settings)

    # ── Engine startup ───────────────────────────────────────────────────

    def _start_engine(self):
        """Load Whisper model on background thread, warm up audio."""
        self._set_status("loading")
        threading.Thread(
            target=self._transcriber.load_model, daemon=True, name="model-load"
        ).start()
        threading.Thread(
            target=AudioCapture.warmup, daemon=True
        ).start()

    # ── Hotkey polling ───────────────────────────────────────────────────

    def _poll_hotkeys(self):
        try:
            self._hotkeys.poll()
            self._hotkey_poll_failed = False
        except Exception:
            if not self._hotkey_poll_failed:
                logger.exception("Hotkey polling failed")
                self._show_status_message("Hotkey error; check logs")
            self._hotkey_poll_failed = True
        self._poll_job = self.after(POLL_MS, self._poll_hotkeys)

    # ── Hotkey events ────────────────────────────────────────────────────

    def _on_hotkey_event(self, event_type: int, keycode: int, flags: int):
        """Handle hotkey events from the event tap (main thread via poll)."""
        from Quartz import kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged

        hk_mod, hk_key = parse_hotkey(self.cfg["hotkey"])
        tg_cfg = self.cfg.get("toggle_hotkey")
        tg_mod, tg_key = parse_hotkey(tg_cfg) if tg_cfg else (0, -1)

        if event_type == kCGEventFlagsChanged:
            if (
                self._state == "recording"
                and not self._toggle_active
                and hk_mod > 0
                and (flags & hk_mod) != hk_mod
            ):
                self._stop_recording()
            return

        # Check push-to-talk hotkey
        if hk_key >= 0 and keycode == hk_key and (flags & hk_mod) == hk_mod:
            if event_type == kCGEventKeyDown:
                self._start_recording()
            elif event_type == kCGEventKeyUp:
                self._stop_recording()
            return

        # Check toggle hotkey
        if tg_key >= 0 and keycode == tg_key and (flags & tg_mod) == tg_mod:
            if event_type == kCGEventKeyDown:
                if self._toggle_active:
                    self._stop_recording()
                else:
                    self._toggle_active = self._start_recording()
            return

    def _start_recording(self):
        if self._state not in ("ready",):
            return False
        if self._audio.start():
            self._set_status("recording")
            play_sound("Tink")
            return True
        return False

    def _stop_recording(self):
        if self._state != "recording":
            return False
        self._toggle_active = False
        self._set_status("transcribing")
        play_sound("Pop")
        threading.Thread(
            target=self._run_transcription, daemon=True, name="transcribe"
        ).start()
        return True

    def _run_transcription(self):
        """Background thread: stop audio + run pipeline."""
        audio = self._audio.stop()
        if audio is not None and len(audio) > 0:
            self._transcriber.transcribe(audio)
        else:
            self._on_engine_status("ready")

    # ── Engine callbacks (may be called from background threads) ─────────

    def _on_engine_status(self, status: str):
        """Thread-safe status update."""
        self.after(0, self._set_status, status)

    def _on_transcription(self, text: str):
        """Called after successful transcription."""
        logger.debug("Transcription: %s", text)

    # ── UI state management ─────────────────────────────────────────────

    def _set_status(self, state: str):
        """Update status indicator. Must be called on main thread."""
        self._state = state
        color, label = STATUS_MAP.get(state, (FG2, state))
        self._status_dot.configure(text_color=color)
        self._status_label.configure(text=label)
        if hasattr(self, "_menubar"):
            self._menubar.set_state(state)

    def _show_status_message(self, message: str, *, color: str = "#FF453A"):
        """Show a temporary status message without changing the app state."""
        self._status_dot.configure(text_color=color)
        self._status_label.configure(text=message)
        self.after(2500, lambda: self._set_status(self._state))

    # ── Settings panel callbacks ─────────────────────────────────────────

    def _on_apply(self):
        """Apply settings changes."""
        w = self._widgets
        new_model = w["model_var"].get()
        new_lang_name = w["lang_var"].get()
        new_lang = w["lang_codes"].get(new_lang_name)

        # Punctuation
        punct = {
            "capitalization": w["cap_var"].get(),
            "smart_quotes": w["sq_var"].get(),
            "trailing_space": w["ts_var"].get(),
        }

        # Update config
        self.cfg["model_size"] = new_model
        self.cfg["language"] = new_lang
        self.cfg["punctuation"] = punct
        save_config(self.cfg)

        # Apply to engine
        self._transcriber.update_punctuation(punct)
        self._transcriber.update_language(new_lang)

        if new_model != self._transcriber.model_size:
            self._transcriber.reload_model(new_model)

    def _on_capture_hotkey(self):
        """Enter hotkey capture mode."""
        self._reset_capture_ui(stop_capture=True)
        self._widgets["hotkey_lbl"].configure(text="Press keys…")
        self._widgets["hotkey_cancel_btn"].pack(side="right", padx=(4, 0))
        self._hotkeys.start_capture(self._on_hotkey_captured)

    def _on_hotkey_captured(self, config: dict):
        """Hotkey captured — update UI and engine."""
        if hotkeys_equal(config, self.cfg.get("toggle_hotkey")):
            self._reset_capture_ui(stop_capture=False)
            self._show_status_message("Hotkeys must be distinct")
            play_sound("Basso")
            return
        self.cfg["hotkey"] = config
        save_config(self.cfg)
        self._widgets["hotkey_lbl"].configure(text=hotkey_display(config))
        self._widgets["hotkey_cancel_btn"].pack_forget()
        self._hotkeys.update_hotkey(config)

    def _on_capture_toggle(self):
        """Enter toggle-hotkey capture mode."""
        self._reset_capture_ui(stop_capture=True)
        self._widgets["toggle_lbl"].configure(text="Press keys…")
        self._widgets["toggle_cancel_btn"].pack(side="right", padx=(4, 0))
        self._hotkeys.start_capture(self._on_toggle_captured)

    def _on_toggle_captured(self, config: dict):
        """Toggle hotkey captured."""
        if hotkeys_equal(config, self.cfg.get("hotkey")):
            self._reset_capture_ui(stop_capture=False)
            self._show_status_message("Hotkeys must be distinct")
            play_sound("Basso")
            return
        self.cfg["toggle_hotkey"] = config
        save_config(self.cfg)
        self._widgets["toggle_lbl"].configure(text=hotkey_display(config))
        self._widgets["toggle_cancel_btn"].pack_forget()
        self._widgets["toggle_clear_btn"].pack(side="right", padx=(4, 0))
        self._hotkeys.update_toggle_hotkey(config)

    def _on_cancel_hotkey_capture(self):
        """Abort hotkey capture and restore current labels."""
        self._reset_capture_ui(stop_capture=True)

    def _on_clear_toggle(self):
        """Clear toggle hotkey."""
        self.cfg["toggle_hotkey"] = None
        save_config(self.cfg)
        self._widgets["toggle_lbl"].configure(text="\u2014")
        self._widgets["toggle_clear_btn"].pack_forget()
        self._hotkeys.update_toggle_hotkey(None)

    def _reset_capture_ui(self, *, stop_capture: bool):
        if stop_capture:
            self._hotkeys.stop_capture()
        self._widgets["hotkey_lbl"].configure(text=hotkey_display(self.cfg["hotkey"]))
        toggle_cfg = self.cfg.get("toggle_hotkey")
        self._widgets["toggle_lbl"].configure(
            text=hotkey_display(toggle_cfg) if toggle_cfg else "\u2014"
        )
        self._widgets["hotkey_cancel_btn"].pack_forget()
        self._widgets["toggle_cancel_btn"].pack_forget()

    def _on_add_hotword(self):
        """Add a hotword to the dictionary file."""
        entry = self._widgets["hw_entry"]
        term = entry.get().strip()
        if not term:
            return
        ensure_dictionary_file()
        with open(DICTIONARY_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{term}")
        entry.delete(0, "end")
        self._refresh_dict_count()

    def _on_add_replacement(self):
        """Add a replacement rule to the dictionary file."""
        wrong = self._widgets["rep_wrong"].get().strip()
        right = self._widgets["rep_right"].get().strip()
        if not wrong or not right:
            return
        ensure_dictionary_file()
        with open(DICTIONARY_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{wrong} \u2192 {right}")
        self._widgets["rep_wrong"].delete(0, "end")
        self._widgets["rep_right"].delete(0, "end")
        self._refresh_dict_count()

    def _on_reload_dictionary(self):
        """Reload dictionary and update term count."""
        self._transcriber.reload_dictionary()
        self._refresh_dict_count()

    def _refresh_dict_count(self):
        """Update the dictionary term count label."""
        dict_data = parse_dictionary(DICTIONARY_FILE)
        self._widgets["term_count_lbl"].configure(
            text=f"{dict_data.term_count} / {MAX_TERMS} terms"
        )

    # ── Menu bar / window management ─────────────────────────────────────

    def _request_show_settings(self):
        """Schedule settings window display on the Tk event loop."""
        self.after(0, self._show_settings)

    def _show_settings(self):
        """Show the settings window."""
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        self.deiconify()
        self.state("normal")
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(150, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self.focus_force()

    def _on_accessibility_error(self):
        """Show alert when event tap creation fails."""
        try:
            from AppKit import NSAlert
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Accessibility Permission Required")
            alert.setInformativeText_(
                "Aside needs Accessibility permission to detect hotkeys.\n\n"
                "Go to System Settings → Privacy & Security → Accessibility "
                "and add your Terminal app."
            )
            alert.runModal()
        except Exception:
            logger.error("Cannot create event tap — check Accessibility permissions")

    def _on_quit(self):
        """Clean shutdown."""
        try:
            self._hotkeys.shutdown()
        except Exception:
            pass
        try:
            if self._lock_fd:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
        except Exception:
            pass
        self.quit()
