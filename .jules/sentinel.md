## 2025-05-01 - [Configuration Permissions Defense in Depth]
**Vulnerability:** The application stored user configuration and custom dictation dictionary rules in `~/.aside/` with standard umask permissions, allowing other system users potential read access to private dictation configurations.
**Learning:** Default permissions given by Python's `Path.mkdir(parents=True)` and file writes rely on the user's `umask`, which is often not sufficiently restrictive (`0o755`/`0o644`) for directories storing personal dictation shortcuts or terms.
**Prevention:** Explicitly use `mode=0o700` with `.mkdir()`, followed immediately by a `.chmod(0o700)` and file `.chmod(0o600)` override when managing custom configuration paths that hold sensitive data like dictation templates.
