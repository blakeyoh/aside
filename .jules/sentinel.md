## 2024-05-15 - Prevent Dictionary Rule Injection
**Vulnerability:** Unsanitized newline characters (`\n`, `\r`) in user input for dictionary hotwords and replacements allowed users to inject arbitrary rules by appending extra lines when modifying the dictionary file.
**Learning:** When appending user input directly to structured text files (like dictionaries or configs), failing to strip newlines can lead to structure manipulation or injection attacks, potentially corrupting the file or allowing unauthorized rules.
**Prevention:** Always sanitize user input intended for single-line fields by stripping or replacing newline characters before writing to structured text files.
