#!/usr/bin/env python3
"""
Lightweight WebSocket health checker for the trading feed.

Usage:
  python3 scripts/ws_monitor.py [threshold_seconds]

Checks the trading log for the most recent WebSocket connected/error/stale events
and reports whether the feed has been disconnected beyond the threshold.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_ts(ts_str: str) -> datetime:
    # Logs use ISO with trailing Z; tolerate missing/invalid values.
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def main():
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    log_path = Path("logs/uvicorn.log")
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        sys.exit(2)

    last_connected = None
    last_error = None
    last_stale = None

    with log_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "WebSocket" not in line and "Tick stream stale" not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            ts = parse_ts(rec.get("timestamp"))
            if ts is None:
                continue

            event = rec.get("event", "")
            if "WebSocket connected" in event:
                last_connected = ts
            elif "WebSocket error" in event:
                last_error = ts
            elif "WebSocket closed" in event:
                last_error = ts  # treat closes as errors for reporting
            elif "Tick stream stale" in event:
                last_stale = ts

    now = datetime.now(timezone.utc)
    status = "OK"
    details = []

    if last_connected:
        seconds_since_connect = (now - last_connected).total_seconds()
        details.append(f"last_connected={last_connected.isoformat()}Z (~{int(seconds_since_connect)}s ago)")
        if seconds_since_connect > threshold:
            status = "STALE"
            details.append(f"stale_over_threshold>{threshold}s")
    else:
        status = "UNKNOWN"
        details.append("no WebSocket connected event found")

    if last_error:
        details.append(f"last_error={last_error.isoformat()}Z")
    if last_stale:
        details.append(f"last_stale={last_stale.isoformat()}Z")

    print(f"{status} | " + " | ".join(details))
    if status != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
