# Sentinel Security Learnings

## 2026-03-24
- **Vulnerability:** OS command/argument injection via `subprocess.run(["open", path])`.
- **Learning:** Spawning a shell or a generic process (even with an argument list) to open files/URLs using the system `open` command introduces risks if the input is not strictly validated. Using `webbrowser.open()` in Python provides a safer, high-level abstraction that delegates the "open" action to the OS-specific handler without the same injection surface as manual `subprocess` calls.
- **Prevention:** Always prefer high-level, purpose-specific APIs (like `webbrowser.open`) over generic process execution (`subprocess`) for interacting with system-registered handlers for files and URLs.
