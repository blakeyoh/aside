"""First-launch permissions onboarding window.

Shows Microphone, Accessibility, and Input Monitoring status rows
with deep-links to System Settings. Polls every 1.5 s while visible.
Can be shown from the Permissions… menu item on subsequent launches.
"""

import logging
from typing import Callable

import customtkinter as ctk

from aside.permissions import (
    PermissionStatus,
    check_accessibility,
    check_input_monitoring,
    check_microphone,
    request_privacy_access,
)
from aside.ui.theme import ACCENT, BG, BG2, FG, FG2, FONT, SEP

logger = logging.getLogger(__name__)

_POLL_MS = 1500

_GREEN = "#30D158"
_RED = "#FF453A"
_GREY = "#8E8E93"

_ROWS = [
    {
        "key": "microphone",
        "label": "Microphone",
        "description": "Capture audio for transcription",
        "pane": "microphone",
    },
    {
        "key": "accessibility",
        "label": "Accessibility",
        "description": "Detect hotkeys via event tap",
        "pane": "accessibility",
    },
    {
        "key": "input_monitoring",
        "label": "Input Monitoring",
        "description": "Read keystrokes from other apps",
        "pane": "input_monitoring",
    },
]

_CHECKERS = {
    "microphone": check_microphone,
    "accessibility": check_accessibility,
    "input_monitoring": check_input_monitoring,
}


class OnboardingWindow(ctk.CTkToplevel):
    """Permission checklist window shown on first launch."""

    def __init__(self, parent: ctk.CTk, on_complete: Callable[[], None]):
        super().__init__(parent)
        self._on_complete = on_complete
        self._poll_job = None
        self._destroyed = False
        self._all_granted = False

        self.title("Aside — Permissions")
        self.geometry("380x480")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._poll()

    # ── UI construction ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 24}

        # Header
        ctk.CTkLabel(
            self,
            text="Welcome to Aside",
            font=(FONT, 20, "bold"),
            text_color=FG,
        ).pack(pady=(28, 4), **pad)

        ctk.CTkLabel(
            self,
            text="Grant these permissions before recording.",
            font=(FONT, 13),
            text_color=FG2,
        ).pack(pady=(0, 20), **pad)

        # Divider
        ctk.CTkFrame(self, fg_color=SEP, height=1, corner_radius=0).pack(
            fill="x", **pad
        )

        # Permission rows
        self._row_widgets: dict[str, dict] = {}
        for row in _ROWS:
            self._row_widgets[row["key"]] = self._build_row(row)
            ctk.CTkFrame(self, fg_color=SEP, height=1, corner_radius=0).pack(
                fill="x", **pad
            )

        # Accessibility restart note
        ctk.CTkLabel(
            self,
            text="After granting Accessibility, restart Aside.",
            font=(FONT, 11),
            text_color=FG2,
        ).pack(pady=(10, 0), **pad)

        # Spacer
        ctk.CTkFrame(self, fg_color="transparent", height=8).pack()

        # Get Started button — disabled until all permissions granted
        self._continue_btn = ctk.CTkButton(
            self,
            text="Get Started  →",
            font=(FONT, 14, "bold"),
            fg_color=ACCENT,
            text_color="#000000",
            hover_color="#00B8CC",
            corner_radius=10,
            height=42,
            width=200,
            state="disabled",
            command=self._on_continue,
        )
        self._continue_btn.pack(pady=(8, 24))

    def _build_row(self, row: dict) -> dict:
        frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame.pack(fill="x", padx=24, pady=10)

        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        dot = ctk.CTkLabel(left, text="●", font=(FONT, 14), text_color=_GREY)
        dot.pack(side="left", padx=(0, 8))

        text_frame = ctk.CTkFrame(left, fg_color="transparent")
        text_frame.pack(side="left")

        ctk.CTkLabel(
            text_frame,
            text=row["label"],
            font=(FONT, 13, "bold"),
            text_color=FG,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_frame,
            text=row["description"],
            font=(FONT, 11),
            text_color=FG2,
            anchor="w",
        ).pack(anchor="w")

        btn = ctk.CTkButton(
            frame,
            text="Open Settings  ↗",
            font=(FONT, 12),
            fg_color=BG2,
            text_color=FG,
            hover_color=SEP,
            corner_radius=8,
            height=30,
            width=130,
            command=lambda p=row["pane"]: request_privacy_access(p),
        )
        btn.pack(side="right")

        return {"dot": dot, "btn": btn}

    # ── Polling ──────────────────────────────────────────────────────────

    def _poll(self) -> None:
        if self._destroyed:
            return
        all_granted = True
        for row in _ROWS:
            status = _CHECKERS[row["key"]]()
            widgets = self._row_widgets[row["key"]]
            if status == PermissionStatus.GRANTED:
                widgets["dot"].configure(text_color=_GREEN)
                widgets["btn"].configure(state="disabled", text_color=_GREY)
            else:
                all_granted = False
                widgets["dot"].configure(text_color=_RED)
                widgets["btn"].configure(state="normal", text_color=FG)

        self._all_granted = all_granted
        if all_granted:
            self._continue_btn.configure(
                state="normal",
                fg_color=_GREEN,
                text_color="#000000",
            )
        else:
            self._continue_btn.configure(
                state="disabled",
                fg_color=ACCENT,
                text_color="#000000",
            )

        self._poll_job = self.after(_POLL_MS, self._poll)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_continue(self) -> None:
        # Only mark onboarding complete when every required permission
        # is granted — otherwise hotkeys/recording silently break and
        # the user has no clear path back to fix it.
        if not self._all_granted:
            return
        self._on_complete()
        self.destroy()

    def _on_close(self) -> None:
        # Closing the window without all permissions granted does not
        # persist first_run_complete, so onboarding reappears next launch.
        if self._all_granted:
            self._on_complete()
        self.destroy()

    def destroy(self) -> None:
        self._destroyed = True
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
        super().destroy()

    # ── Public ───────────────────────────────────────────────────────────

    def show(self) -> None:
        """Bring window to the front."""
        try:
            from AppKit import NSApplication

            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        self.deiconify()
        self.lift()
        self.focus_force()
