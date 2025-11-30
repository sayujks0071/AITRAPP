#!/usr/bin/env python3
"""
Morning preflight for Zerodha Kite stack.

Checks:
  - Kite API key/token present and usable (profile call)
  - Instrument cache exists for today (if caching enabled)
  - Sidecar /health returns 200

Exit code 0 on success; non-zero on any failure.
"""
import os
import sys
import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests not installed. Activate venv and install requirements.", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv
from kiteconnect import KiteConnect


def check_env_tokens() -> list[str]:
    missing = []
    if not os.getenv("KITE_API_KEY"):
        missing.append("KITE_API_KEY")
    if not os.getenv("KITE_ACCESS_TOKEN"):
        missing.append("KITE_ACCESS_TOKEN")
    return missing


def check_kite_profile() -> tuple[bool, str]:
    try:
        kite = KiteConnect(api_key=os.getenv("KITE_API_KEY"))
        kite.set_access_token(os.getenv("KITE_ACCESS_TOKEN"))
        profile = kite.profile()
        user_id = profile.get("user_id", "unknown")
        return True, f"Kite profile OK (user_id={user_id})"
    except Exception as e:
        return False, f"Kite profile check failed: {e}"


def check_instrument_cache() -> tuple[bool, str]:
    cache_enabled = os.getenv("INSTRUMENT_CACHE_ENABLED", "1") == "1"
    if not cache_enabled:
        return True, "Instrument cache disabled; skipping cache check"
    cache_dir = Path(os.getenv("INSTRUMENT_CACHE_DIR", "data/instruments"))
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    expected = cache_dir / f"instruments_{today}.csv"
    if expected.exists():
        return True, f"Instrument cache present: {expected}"
    return False, f"Instrument cache missing for today: {expected}"


def check_sidecar_health() -> tuple[bool, str]:
    port = os.getenv("SIDECAR_PORT", "8080")
    url = os.getenv("SIDECAR_HEALTH_URL", f"http://localhost:{port}/health")
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            return True, f"Sidecar health OK ({url})"
        return False, f"Sidecar health returned {resp.status_code} ({url})"
    except Exception as e:
        return False, f"Sidecar health check failed ({url}): {e}"


def main() -> int:
    load_dotenv()

    failures = []
    warnings = []

    missing = check_env_tokens()
    if missing:
        failures.append(f"Missing env vars: {', '.join(missing)}")

    ok, msg = check_kite_profile()
    (warnings if ok else failures).append(msg)

    ok, msg = check_instrument_cache()
    (warnings if ok else failures).append(msg)

    ok, msg = check_sidecar_health()
    (warnings if ok else failures).append(msg)

    for w in warnings:
        print(f"⚠️  {w}")
    if failures:
        for f in failures:
            print(f"❌ {f}")
        return 1

    print("✅ Morning check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
