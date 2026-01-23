## 2024-05-23 - Hardcoded Secrets in Utility Scripts
**Vulnerability:** Found hardcoded Kite Connect API Key and API Secret in `get_kite_token.py`.
**Learning:** Utility scripts, often treated as "temporary" or "local-only", are common places for hardcoded secrets to hide and get committed to version control.
**Prevention:** Ensure all scripts, even utilities, use environment variables or prompt for sensitive inputs. Add pre-commit hooks to scan for high-entropy strings or known key patterns.

## 2024-05-24 - Hardcoded Secrets in Setup Scripts
**Vulnerability:** Found hardcoded Kite API credentials in `setup_claude_mcp.sh` embedded python script.
**Learning:** Setup scripts that generate configuration files might be tempted to include "default" or "test" credentials which can accidentally be real credentials.
**Prevention:** Always force the user to input their own credentials or read from the environment, even in "easy setup" scripts. Never include "example" secrets that look like real high-entropy strings.

## 2026-01-13 - Path Traversal Vulnerability in Data Loader
**Vulnerability:** Found `HistoricalDataLoader.load_file` accepting arbitrary strings for `symbol`, potentially allowing directory traversal via `../` if prefixes were changed or exploited.
**Learning:** Implicit trust in API inputs passed to file operations is a common pattern even when prefixes exist. Defensive programming requires explicit validation.
**Prevention:** Added regex validation `^[a-zA-Z0-9_-]+$` to `HistoricalDataLoader` inputs. Always validate inputs at the boundary before they reach sensitive operations like file I/O.

## 2026-05-27 - Hardcoded Realistic Secrets in Documentation
**Vulnerability:** Found realistic-looking high-entropy API keys and secrets hardcoded in multiple markdown documentation files (`MCP_SERVER_SETUP.md`, `MCP_AUTHENTICATION_GUIDE.md`, etc.).
**Learning:** Copy-pasting "working" examples into documentation without scrubbing sensitive data is a common source of leaks. Developers often forget that documentation is code and is public.
**Prevention:** Always use obvious placeholders (e.g., `<YOUR_API_KEY>`) in documentation.

## 2025-05-27 - DoS Vulnerability in Blocking Sync Endpoints
**Vulnerability:** Found synchronous  called directly within async endpoint . This blocked the entire asyncio event loop, causing Denial of Service for critical endpoints like .
**Learning:** Mixing synchronous CPU-bound code with async endpoints is a classic DoS vector in Python web frameworks (FastAPI/Starlette). The GIL ensures the main thread (event loop) is blocked.
**Prevention:** Always offload blocking/CPU-intensive tasks to a thread pool using  or . Also enforce input validation limits (e.g. max date range) to prevent resource exhaustion even in threads.

## 2025-05-27 - DoS Vulnerability in Blocking Sync Endpoints
**Vulnerability:** Found synchronous `BacktestEngine.run_backtest` called directly within async endpoint `/backtest`. This blocked the entire asyncio event loop, causing Denial of Service for critical endpoints like `/flatten`.
**Learning:** Mixing synchronous CPU-bound code with async endpoints is a classic DoS vector in Python web frameworks (FastAPI/Starlette). The GIL ensures the main thread (event loop) is blocked.
**Prevention:** Always offload blocking/CPU-intensive tasks to a thread pool using `run_in_threadpool` or `loop.run_in_executor`. Also enforce input validation limits (e.g. max date range) to prevent resource exhaustion even in threads.
