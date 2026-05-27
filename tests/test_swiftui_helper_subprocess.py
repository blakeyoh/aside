import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Spawns a real `python -m aside.helper` subprocess, which imports the native
# audio stack (numpy/sounddevice) at module load. Those aren't available off
# macOS and in-process conftest stubs don't reach the child, so skip here and
# rely on the macOS CI workflow to exercise it.
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="helper subprocess needs the real macOS native stack; covered by macOS CI",
)


def test_helper_entrypoint_reports_permissions_and_shuts_down_cleanly():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHONUNBUFFERED"] = "1"
    env["ASIDE_HELPER_PROTOCOL_SMOKE"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "aside.helper"],
        cwd=repo_root,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        events = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            events.append(json.loads(line))
            if any(event.get("type") == "status" and event.get("state") == "ready" for event in events):
                break

        assert any(event.get("type") == "hello" for event in events)
        assert any(event.get("type") == "permissions" for event in events)
        assert any(
            event.get("type") == "status" and event.get("state") == "loading"
            for event in events
        )
        assert any(
            event.get("type") == "status" and event.get("state") == "ready"
            for event in events
        )

        proc.stdin.write(json.dumps({"command": "shutdown"}) + "\n")
        proc.stdin.flush()

        remaining_stdout, stderr = proc.communicate(timeout=5)
        for line in remaining_stdout.splitlines():
            events.append(json.loads(line))

        assert proc.returncode == 0, stderr
        assert events[-1]["type"] == "exit"
    finally:
        if proc.poll() is None:
            proc.kill()
