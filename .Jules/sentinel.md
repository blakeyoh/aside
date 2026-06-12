# Sentinel Security Learnings

## 2026-03-24
- **Vulnerability:** OS command/argument injection via `subprocess.run(["open", path])`.
- **Learning:** Spawning a shell or a generic process (even with an argument list) to open files/URLs using the system `open` command introduces risks if the input is not strictly validated. Using `webbrowser.open()` in Python provides a safer, high-level abstraction that delegates the "open" action to the OS-specific handler without the same injection surface as manual `subprocess` calls.
- **Prevention:** Always prefer high-level, purpose-specific APIs (like `webbrowser.open`) over generic process execution (`subprocess`) for interacting with system-registered handlers for files and URLs.

## 2026-06-12 - [Missing Input Validation before System Preference Deep-Linking]
- **Vulnerability:** Unhandled KeyError and potential invalid input leading to system state changes when launching system preferences URLs based on unbounded dictionary keys (`_PANES[pane]`).
- **Learning:** Bypassing input validation when accessing dictionary keys to construct arguments for system URL handlers (such as `x-apple.systempreferences`) could be leveraged to cause application crashes or to unintentionally open unsupported configurations if input sanitization is missed.
- **Prevention:** Always validate user-provided or external inputs against known safe parameters before constructing system URLs or executing commands. Specifically, use safe dictionary access (`.get()`) and explicitly handle unexpected values by logging and returning safely.
