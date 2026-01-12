## 2024-05-23 - Hardcoded Secrets in Utility Scripts
**Vulnerability:** Found hardcoded Kite Connect API Key and API Secret in `get_kite_token.py`.
**Learning:** Utility scripts, often treated as "temporary" or "local-only", are common places for hardcoded secrets to hide and get committed to version control.
**Prevention:** Ensure all scripts, even utilities, use environment variables or prompt for sensitive inputs. Add pre-commit hooks to scan for high-entropy strings or known key patterns.

## 2024-05-24 - Hardcoded Secrets in Setup Scripts
**Vulnerability:** Found hardcoded Kite API credentials in `setup_claude_mcp.sh` embedded python script.
**Learning:** Setup scripts that generate configuration files might be tempted to include "default" or "test" credentials which can accidentally be real credentials.
**Prevention:** Always force the user to input their own credentials or read from the environment, even in "easy setup" scripts. Never include "example" secrets that look like real high-entropy strings.
