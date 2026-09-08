# Sentinel Security Learnings

## 2024-05-15 - Prevent Dictionary Rule Injection

- **Vulnerability:** Unsanitized newline characters (`\n`, `\r`) in user input for dictionary hotwords and replacements allowed users to inject arbitrary rules by appending extra lines when modifying the dictionary file.
- **Learning:** When appending user input directly to structured text files (like dictionaries or configs), failing to strip newlines can lead to structure manipulation or injection attacks, potentially corrupting the file or allowing unauthorized rules.
- **Prevention:** Always sanitize user input intended for single-line fields by stripping or replacing newline characters before writing to structured text files.

## 2024-05-20 - Enforce strict permissions and defensive input checking

- **Vulnerability:** Configuration directories and sensitive dictionary files lacked enforced strict permissions, and `open_privacy_pane` accessed the `_PANES` mapping without validating the lookup.
- **Learning:** Explicit `0o700` directory and `0o600` file permissions protect local user data. Mapping lookups should reject unknown keys before opening a system URL.
- **Prevention:** Enforce least privilege when creating and mutating user data, and validate native-system inputs before use.

## 2026-03-24 - Prefer purpose-specific URL opening APIs

- **Vulnerability:** Opening files or URLs with a generic `subprocess.run(["open", path])` call creates avoidable argument-injection risk.
- **Learning:** `webbrowser.open()` delegates to the registered OS handler without exposing the same generic process interface.
- **Prevention:** Prefer high-level, purpose-specific APIs over generic process execution for system-registered files and URLs.

## 2026-05-27 - Sanitize dictionary IPC input

- **Vulnerability:** UI or IPC input written directly to `dictionary.txt` could inject new rules through newline characters.
- **Learning:** Every command boundary that writes a line-oriented format must enforce its one-line contract.
- **Prevention:** Strip or reject newline and carriage-return characters before dictionary values reach persistence.
