"""UI constants: colors, fonts, layout values."""

BG = "#1C1C1E"
BG2 = "#2C2C2E"
FG = "#F2F2F7"
FG2 = "#8E8E93"
ACCENT = "#00E5FF"
SEP = "#3A3A3C"
FONT = "SF Pro Display"
MONO = "SF Mono"

POLL_MS = 10  # engine keyboard event polling interval

STATUS_MAP = {
    "loading": ("#FF9F0A", "Loading model…"),
    "ready": ("#30D158", "Ready"),
    "recording": ("#FF453A", "Recording…"),
    "transcribing": ("#0A84FF", "Transcribing…"),
}

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
MODEL_LABELS = {
    "tiny": "tiny  (~39 MB)  · fastest, lower accuracy",
    "base": "base  (~140 MB)  · balanced  ← recommended",
    "small": "small  (~460 MB)  · better accuracy",
    "medium": "medium  (~1.5 GB)  · high accuracy",
    "large-v3": "large-v3  (~3 GB)  · best accuracy",
}

MOD_SYMBOLS = {"ctrl": "⌃", "alt": "⌥", "cmd": "⌘", "shift": "⇧"}
KEY_DISPLAY = {
    "space": "Space",
    "return": "Return",
    "tab": "Tab",
    "backspace": "⌫",
    "escape": "Esc",
}

# faster-whisper supported languages (common subset for dropdown)
LANGUAGES = [
    ("Auto-detect", None),
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Russian", "ru"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Arabic", "ar"),
    ("Hindi", "hi"),
    ("Turkish", "tr"),
    ("Polish", "pl"),
    ("Swedish", "sv"),
    ("Danish", "da"),
    ("Norwegian", "no"),
    ("Finnish", "fi"),
    ("Czech", "cs"),
]
