"""Shared single-engine ownership for native and legacy Aside entry points."""

from __future__ import annotations

import fcntl
import logging
from pathlib import Path
from typing import IO

from aside.config import CONFIG_DIR

logger = logging.getLogger(__name__)

ENGINE_LOCK_FILE = CONFIG_DIR / "aside.lock"


def acquire_engine_lock(lock_file: Path | None = None) -> IO[str] | None:
    """Acquire the one cross-process lock that owns hotkeys/audio/injection."""
    path = lock_file or ENGINE_LOCK_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.info("Could not create Aside engine-lock directory %s: %s", path, exc)
        return None
    try:
        path.parent.chmod(0o700)
    except OSError:
        logger.warning("Could not enforce 0o700 on %s", path.parent)
    try:
        handle = path.open("w", encoding="utf-8")
    except OSError as exc:
        logger.info("Could not open Aside engine lock at %s: %s", path, exc)
        return None
    try:
        path.chmod(0o600)
    except OSError:
        logger.warning("Could not enforce 0o600 on %s", path)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError as exc:
        logger.info("Aside engine lock unavailable at %s: %s", path, exc)
        handle.close()
        return None


def release_engine_lock(handle: IO[str] | None) -> None:
    """Release a lock returned by acquire_engine_lock; safe during teardown."""
    if handle is None:
        return
    try:
        fcntl.flock(handle, fcntl.LOCK_UN)
    except OSError:
        logger.debug("Could not unlock Aside engine lock", exc_info=True)
    try:
        handle.close()
    except OSError:
        logger.debug("Could not close Aside engine lock", exc_info=True)
