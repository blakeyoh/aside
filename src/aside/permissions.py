"""macOS permission checks and System Settings deep-links.

All functions are pure and side-effect-free except open_privacy_pane(),
which launches System Settings. Safe to call from any thread.
"""
import ctypes
import logging
import webbrowser
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


def request_accessibility() -> PermissionStatus:
    """Ask macOS to prompt for Accessibility access, then return current status."""
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception:
        logger.debug("Unable to request Accessibility access", exc_info=True)
    return check_accessibility()


# IOKit constants from <IOKit/hid/IOHIDLib.h>:
#   kIOHIDRequestTypeListenEvent = 1
#   kIOHIDAccessTypeGranted = 0, Denied = 1, Unknown = 2
# pyobjc does not ship a pyobjc-framework-IOKit subpackage, so we link
# against the framework directly via ctypes to avoid an install-time dep
# that fails resolution.
_IOKIT_PATH = "/System/Library/Frameworks/IOKit.framework/IOKit"
_IOHID_REQUEST_TYPE_LISTEN_EVENT = 1


def _check_input_monitoring_iohid() -> PermissionStatus:
    try:
        lib = ctypes.CDLL(_IOKIT_PATH)
        lib.IOHIDCheckAccess.restype = ctypes.c_uint32
        lib.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        result = int(lib.IOHIDCheckAccess(_IOHID_REQUEST_TYPE_LISTEN_EVENT))
    except Exception:
        logger.debug("IOHIDCheckAccess unavailable; assuming input monitoring not determined")
        return PermissionStatus.NOT_DETERMINED
    if result == 0:
        return PermissionStatus.GRANTED
    if result == 1:
        return PermissionStatus.DENIED
    return PermissionStatus.NOT_DETERMINED


def check_input_monitoring() -> PermissionStatus:
    """Query keyboard listen-event access for Input Monitoring."""
    try:
        from Quartz import CGPreflightListenEventAccess
        if bool(CGPreflightListenEventAccess()):
            return PermissionStatus.GRANTED
    except Exception:
        logger.debug("CGPreflightListenEventAccess unavailable", exc_info=True)

    return _check_input_monitoring_iohid()


def request_input_monitoring() -> PermissionStatus:
    """Ask macOS to prompt for Input Monitoring access, then return current status."""
    try:
        from Quartz import CGRequestListenEventAccess
        if bool(CGRequestListenEventAccess()):
            return PermissionStatus.GRANTED
    except Exception:
        logger.debug("CGRequestListenEventAccess unavailable", exc_info=True)

    try:
        lib = ctypes.CDLL(_IOKIT_PATH)
        lib.IOHIDRequestAccess.restype = ctypes.c_bool
        lib.IOHIDRequestAccess.argtypes = [ctypes.c_uint32]
        if bool(lib.IOHIDRequestAccess(_IOHID_REQUEST_TYPE_LISTEN_EVENT)):
            return PermissionStatus.GRANTED
    except Exception:
        logger.debug("IOHIDRequestAccess unavailable", exc_info=True)

    return check_input_monitoring()


_PANES = {
    "microphone":       "com.apple.preference.security?Privacy_Microphone",
    "accessibility":    "com.apple.preference.security?Privacy_Accessibility",
    "input_monitoring": "com.apple.preference.security?Privacy_ListenEvent",
}


def open_privacy_pane(pane: str) -> None:
    """Open the matching Privacy pane in System Settings / System Preferences."""
    pane_path = _PANES.get(pane)
    if not pane_path:
        logger.error(f"Unknown privacy pane requested: {pane}")
        return
    url = f"x-apple.systempreferences:{pane_path}"
    webbrowser.open(url)


def request_privacy_access(pane: str) -> PermissionStatus | None:
    """Request a permission via native prompt when possible, then open Settings."""
    status = None
    if pane == "accessibility":
        status = request_accessibility()
    elif pane == "input_monitoring":
        status = request_input_monitoring()

    if status != PermissionStatus.GRANTED:
        open_privacy_pane(pane)
    return status
