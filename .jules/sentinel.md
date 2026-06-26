## 2024-05-15 - Prevent Dictionary Rule Injection
**Vulnerability:** Unsanitized newline characters (`\n`, `\r`) in user input for dictionary hotwords and replacements allowed users to inject arbitrary rules by appending extra lines when modifying the dictionary file.
**Learning:** When appending user input directly to structured text files (like dictionaries or configs), failing to strip newlines can lead to structure manipulation or injection attacks, potentially corrupting the file or allowing unauthorized rules.
**Prevention:** Always sanitize user input intended for single-line fields by stripping or replacing newline characters before writing to structured text files.

## 2024-05-16 - Safe Dictionary Lookups for System URIs
**Vulnerability:** Unvalidated dictionary lookups (`_PANES[pane]`) when constructing system URIs could lead to unhandled `KeyError` exceptions (DoS) or unexpected system behavior if an unknown pane was requested.
**Learning:** When using user-provided or dynamic input to key into a dictionary for constructing sensitive operations like system URIs or executing commands, strict validation is required to prevent unhandled exceptions or unintended command execution.
**Prevention:** Always use `.get()` or explicit validation against allowed keys before constructing system URIs, logging an error and aborting the operation for invalid inputs.
