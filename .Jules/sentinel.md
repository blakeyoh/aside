# Sentinel Security Learnings

## 2026-03-24
- **Vulnerability:** OS command/argument injection via `subprocess.run(["open", path])`.
- **Learning:** Spawning a shell or a generic process (even with an argument list) to open files/URLs using the system `open` command introduces risks if the input is not strictly validated. Using `webbrowser.open()` in Python provides a safer, high-level abstraction that delegates the "open" action to the OS-specific handler without the same injection surface as manual `subprocess` calls.
- **Prevention:** Always prefer high-level, purpose-specific APIs (like `webbrowser.open`) over generic process execution (`subprocess`) for interacting with system-registered handlers for files and URLs.

## 2024-05-20 - Enforce strict permissions for config dir and use defensive input checking
**Vulnerability:** Configuration directory and sensitive dict files lacked enforced strict permissions upon creation/mutation. `open_privacy_pane` also accessed `_PANES` dict unsafely.
**Learning:** Hardcoding or relying on default directory/file permissions on OS environments opens up sensitive data to attack, and unstructured system URLs mapped dynamically from dicts may cause app crashes and potential arbitrary link building. Applying `0o700` and `0o600` ensures strict boundaries. Using `.get()` provides safety for lookup validation.
**Prevention:** Always enforce least privilege explicitly (`0o700` for config dirs, `0o600` for files) when managing user data, and validate inputs before passing to native system interactions (e.g. `webbrowser.open`).
