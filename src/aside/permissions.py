"""macOS permission checks and System Settings deep-links.

All functions are pure and side-effect-free except open_privacy_pane(),
which launches System Settings. Safe to call from any thread.
"""
import ctypes
import logging
import subprocess
from enum import Enum, auto

logger = logging.getLogger(__name__)


class PermissionStatus(Enum):
    GRANTED = auto()
    DENIED = auto()
    NOT_DETERMINED = auto()


def check_microphone() -> PermissionStatus:
    """Query AVFoundation authorization status for audio input."""
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        # 0=NotDetermined, 1=Restricted, 2=Denied, 3=Authorized
        if status == 3:
            return PermissionStatus.GRANTED
        if status in (1, 2):
            return PermissionStatus.DENIED
        return PermissionStatus.NOT_DETERMINED
    except Exception:
        logger.debug("AVFoundation unavailable; assuming mic not determined")
        return PermissionStatus.NOT_DETERMINED


def check_accessibility() -> PermissionStatus:
    """Check whether the process is trusted for accessibility (AXIsProcessTrusted)."""
    try:
        from ApplicationServices import AXIsProcessTrusted
        trusted = AXIsProcessTrusted()
    except ImportError:
        # AXIsProcessTrusted lives in ApplicationServices, which ships inside
        # pyobjc-framework-Quartz. Fall back to ctypes if the binding is absent.
        try:
            _lib = ctypes.CDLL(
                "/System/Library/Frameworks/ApplicationServices.framework/"
                "ApplicationServices"
            )
            _lib.AXIsProcessTrusted.restype = ctypes.c_bool
            trusted = _lib.AXIsProcessTrusted()
        except Exception:
            logger.debug("AXIsProcessTrusted unavailable")
            return PermissionStatus.NOT_DETERMINED
    return PermissionStatus.GRANTED if trusted else PermissionStatus.DENIED


# IOKit constants from <IOKit/hid/IOHIDLib.h>:
#   kIOHIDRequestTypeListenEvent = 1
#   kIOHIDAccessTypeGranted = 0, Denied = 1, Unknown = 2
# pyobjc does not ship a pyobjc-framework-IOKit subpackage, so we link
# against the framework directly via ctypes to avoid an install-time dep
# that fails resolution.
_IOKIT_PATH = "/System/Library/Frameworks/IOKit.framework/IOKit"
_IOHID_REQUEST_TYPE_LISTEN_EVENT = 1


def check_input_monitoring() -> PermissionStatus:
    """Query IOHIDCheckAccess for keyboard listen-event access."""
    try:
        lib = ctypes.CDLL(_IOKIT_PATH)
        lib.IOHIDCheckAccess.restype = ctypes.c_uint32
        lib.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        result = int(lib.IOHIDCheckAccess(_IOHID_REQUEST_TYPE_LISTEN_EVENT))
    except Exception:
        logger.debug("IOHIDCheckAccess unavailable; assuming input monitoring not determined")
        return PermissionStatus.NOT_DETERMINED
    if result in (0, 3):
        return PermissionStatus.GRANTED
    if result == 1:
        return PermissionStatus.DENIED
    return PermissionStatus.NOT_DETERMINED


_PANES = {
    "microphone":       "com.apple.preference.security?Privacy_Microphone",
    "accessibility":    "com.apple.preference.security?Privacy_Accessibility",
    "input_monitoring": "com.apple.preference.security?Privacy_ListenEvent",
}


def open_privacy_pane(pane: str) -> None:
    """Open the matching Privacy pane in System Settings / System Preferences."""
    url = f"x-apple.systempreferences:{_PANES[pane]}"
    subprocess.run(["open", url], check=False)
