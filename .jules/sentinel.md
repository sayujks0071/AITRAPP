## 2024-05-23 - Hardcoded Secrets in Utility Scripts
**Vulnerability:** Found hardcoded Kite Connect API Key and API Secret in `get_kite_token.py`.
**Learning:** Utility scripts, often treated as "temporary" or "local-only", are common places for hardcoded secrets to hide and get committed to version control.
**Prevention:** Ensure all scripts, even utilities, use environment variables or prompt for sensitive inputs. Add pre-commit hooks to scan for high-entropy strings or known key patterns.
