## 2024-05-02 - Secure File Permissions
**Vulnerability:** Insufficient file permissions for configuration directory and files.
**Learning:** Sensitive configuration files (`config.json`, `dictionary.txt`, `aside.lock`) and their parent directory were created with default permissions, which could expose user data to other users on the system.
**Prevention:** Enforce strict file permissions when creating configuration directories (e.g., `0o700`) and files (e.g., `0o600`) to implement Defense in Depth and prevent unauthorized local access.
