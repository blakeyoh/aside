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
import queue
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
from aside.ui.onboarding import OnboardingWindow
from aside.ui.settings import build_settings
from aside.ui.theme import BG, FG, FG2, FONT, ACCENT, POLL_MS, STATUS_MAP

logger = logging.getLogger(__name__)

ICON_PATH = resource_path("aside-logo.png")
LOCK_FILE = CONFIG_DIR / "aside.lock"
UI_ACTION_SHOW_SETTINGS = "show_settings"
UI_ACTION_SHOW_ONBOARDING = "show_onboarding"


def initial_launch_target(config: dict) -> str:
    """Return the first visible surface to show after startup."""
    return "settings" if config.get("first_run_complete") else "onboarding"


def register_macos_reopen_handlers(root, callback) -> tuple[str, ...]:
    """Register Tk macOS app-menu callbacks that reopen the settings window."""
    if sys.platform != "darwin":
        return ()

    registered = []
    for command_name in ("tk::mac::ReopenApplication", "tk::mac::ShowPreferences"):
        try:
            root.createcommand(command_name, callback)
            registered.append(command_name)
        except Exception:
            logger.debug("Unable to register %s", command_name, exc_info=True)
    return tuple(registered)


def scroll_units_from_delta(delta, platform: str = sys.platform) -> int:
    """Convert a Tk MouseWheel delta into conservative canvas scroll units."""
    try:
        numeric_delta = float(delta)
    except (TypeError, ValueError):
        return 0

    if numeric_delta == 0:
        return 0

    if platform.startswith("win"):
        magnitude = int(abs(numeric_delta) / 120)
    else:
        magnitude = int(abs(numeric_delta))

    magnitude = max(1, min(magnitude, 12))
    return -magnitude if numeric_delta > 0 else magnitude


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
        self._is_quitting = False
        self._ui_actions: queue.Queue[str] = queue.Queue()

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
        self._settings_scroll_canvas = getattr(scroll, "_parent_canvas", None)
        self._widgets = build_settings(self, scroll)
        self._bind_settings_mousewheel(scroll)

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

        self._widgets["hw_entry"].bind("<KeyRelease>", self._check_hw_add_state)
        self._widgets["rep_wrong"].bind("<KeyRelease>", self._check_rep_add_state)
        self._widgets["rep_right"].bind("<KeyRelease>", self._check_rep_add_state)

        self._widgets["hw_entry"].bind("<Return>", lambda e: self._on_add_hotword())
        self._widgets["rep_wrong"].bind("<Return>", lambda e: self._on_rep_wrong_return())
        self._widgets["rep_right"].bind("<Return>", lambda e: self._on_add_replacement())

        # ── Onboarding window reference ──────────────────────────────────
        self._onboarding: OnboardingWindow | None = None

        # ── Engine components ────────────────────────────────────────────
        self._audio = AudioCapture(on_mic_denied=self._on_mic_denied)
        self._transcriber = Transcriber(
            model_size=self.cfg["model_size"],
            language=self.cfg.get("language"),
            punctuation_config=self.cfg.get("punctuation"),
            hotwords=self.cfg.get("hotwords"),
            replacements=self.cfg.get("replacements"),
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
            permissions_callback=self._request_show_onboarding,
        )

        # ── Window protocol ─────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self._macos_reopen_commands = register_macos_reopen_handlers(
            self, self._request_show_settings
        )

        # ── Kick off engine ─────────────────────────────────────────────
        self.after_idle(self._start_engine)
        self._poll_job = self.after(POLL_MS, self._poll_hotkeys)
        self._ui_action_poll_job = self.after(POLL_MS, self._poll_ui_actions)
        self.after(300, self._show_initial_window)

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

    def _poll_ui_actions(self):
        """Drain AppKit menu requests on the Tk event loop."""
        try:
            while True:
                try:
                    action = self._ui_actions.get_nowait()
                except queue.Empty:
                    break

                try:
                    if action == UI_ACTION_SHOW_SETTINGS:
                        self._show_settings()
                    elif action == UI_ACTION_SHOW_ONBOARDING:
                        self._show_onboarding()
                    else:
                        logger.warning("Unknown UI action token: %s", action)
                except Exception:
                    logger.exception("UI action handler failed for token: %s", action)
        finally:
            if not self._is_quitting:
                self._ui_action_poll_job = self.after(POLL_MS, self._poll_ui_actions)

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

    def _bind_settings_mousewheel(self, scroll):
        """Route trackpad/mouse wheel events from settings children to the canvas."""
        bound = set()

        def bind_tree(widget):
            if widget is None or id(widget) in bound:
                return
            bound.add(id(widget))
            try:
                widget.bind("<MouseWheel>", self._on_settings_mousewheel, add="+")
            except Exception:
                logger.debug("Unable to bind mouse wheel for %r", widget, exc_info=True)
            try:
                children = widget.winfo_children()
            except Exception:
                children = ()
            for child in children:
                bind_tree(child)

        bind_tree(scroll)
        bind_tree(getattr(scroll, "_parent_frame", None))
        bind_tree(getattr(scroll, "_parent_canvas", None))
        try:
            self.bind("<MouseWheel>", self._on_settings_mousewheel, add="+")
        except Exception:
            logger.debug("Unable to bind mouse wheel for settings window", exc_info=True)

    def _on_settings_mousewheel(self, event):
        canvas = getattr(self, "_settings_scroll_canvas", None)
        if canvas is None:
            return None
        try:
            if canvas.yview() == (0.0, 1.0):
                return None
            units = scroll_units_from_delta(getattr(event, "delta", 0), sys.platform)
            if units == 0:
                return None
            canvas.yview_scroll(units, "units")
            return "break"
        except Exception:
            logger.debug("Settings mouse wheel event failed", exc_info=True)
            return None

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

        self._show_status_message("Settings applied", color="#30D158")

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

    def _check_hw_add_state(self, event=None):
        """Enable hotword add button only if text exists."""
        term = self._widgets["hw_entry"].get().strip()
        self._widgets["hw_add_btn"].configure(state="normal" if term else "disabled")

    def _check_rep_add_state(self, event=None):
        """Enable replacement add button only if both inputs have text."""
        wrong = self._widgets["rep_wrong"].get().strip()
        right = self._widgets["rep_right"].get().strip()
        self._widgets["rep_add_btn"].configure(state="normal" if wrong and right else "disabled")

    def _on_rep_wrong_return(self):
        """Handle return key in replacement 'wrong' field."""
        if not self._widgets["rep_right"].get().strip():
            self._widgets["rep_right"].focus()
        else:
            self._on_add_replacement()

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
        self._check_hw_add_state()
        self._refresh_dict_count()
        self._show_status_message("Hotword added", color="#30D158")
        entry.focus()

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
        self._check_rep_add_state()
        self._refresh_dict_count()
        self._show_status_message("Replacement added", color="#30D158")
        self._widgets["rep_wrong"].focus()

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
        """Enqueue settings display from AppKit without touching Tk."""
        self._ui_actions.put(UI_ACTION_SHOW_SETTINGS)

    def _request_show_onboarding(self):
        """Enqueue onboarding display from AppKit without touching Tk."""
        self._ui_actions.put(UI_ACTION_SHOW_ONBOARDING)

    def _show_initial_window(self):
        """Show a visible launch surface so startup never looks silent."""
        if initial_launch_target(self.cfg) == "onboarding":
            self._show_onboarding()
        else:
            self._show_settings()

    def _show_onboarding(self):
        """Show (or re-show) the permissions onboarding window."""
        if self._onboarding is not None:
            try:
                self._onboarding.show()
                return
            except Exception:
                self._onboarding = None
        self._onboarding = OnboardingWindow(
            self, on_complete=self._on_onboarding_complete
        )
        self._onboarding.show()

    def _on_onboarding_complete(self):
        """Mark first run done and persist."""
        self.cfg["first_run_complete"] = True
        save_config(self.cfg)
        self.after(100, self._show_settings)

    def _on_mic_denied(self):
        """Called by AudioCapture when mic access is denied; open onboarding."""
        self._ui_actions.put(UI_ACTION_SHOW_ONBOARDING)

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
        """Show onboarding window when event tap creation fails."""
        self._ui_actions.put(UI_ACTION_SHOW_ONBOARDING)

    def _on_quit(self):
        """Clean shutdown."""
        self._is_quitting = True
        for job_attr in ("_poll_job", "_ui_action_poll_job"):
            job = getattr(self, job_attr, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
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
