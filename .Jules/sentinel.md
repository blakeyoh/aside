# Sentinel Security Learnings

## 2026-03-24
- **Vulnerability:** OS command/argument injection via `subprocess.run(["open", path])`.
- **Learning:** Spawning a shell or a generic process (even with an argument list) to open files/URLs using the system `open` command introduces risks if the input is not strictly validated. Using `webbrowser.open()` in Python provides a safer, high-level abstraction that delegates the "open" action to the OS-specific handler without the same injection surface as manual `subprocess` calls.
- **Prevention:** Always prefer high-level, purpose-specific APIs (like `webbrowser.open`) over generic process execution (`subprocess`) for interacting with system-registered handlers for files and URLs.

## 2026-05-21 - Defense in Depth: Secure File Permissions
**Vulnerability:** Configuration files (`config.json`, `dictionary.txt`) and lock files (`aside.lock`) were created in a directory (`~/.aside`) relying solely on the user's `umask`, potentially exposing sensitive data like keystrokes and configuration details.
**Learning:** Local applications that store user data must explicitly set restrictive permissions (0o700 for directories, 0o600 for files) to enforce defense in depth and protect against privilege escalation or lateral movement attacks where another user might read sensitive configuration.
**Prevention:** Always pair `mkdir(parents=True, exist_ok=True)` with explicitly passing `mode=0o700` and immediately enforcing `chmod(0o700)` on directories, and `chmod(0o600)` on sensitive files upon creation.
