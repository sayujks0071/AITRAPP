#!/usr/bin/env python3
"""
Lightweight watcher for paper trading health/compliance.

Checks /health, /ready, /state, and /compliance/status in a loop and surfaces
quick alerts (paused, not ready, static IP issues, websocket disconnects).
"""

import argparse
import sys
import time
from typing import Any, Dict

import requests


def fetch_json(url: str) -> Dict[str, Any]:
    """GET a URL and return JSON (or minimal error info)."""
    try:
        resp = requests.get(url, timeout=3)
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        data["http_status"] = resp.status_code
        return data
    except Exception as exc:  # network/connection errors
        return {"error": str(exc), "http_status": None}


def fmt_number(val: Any) -> str:
    if isinstance(val, (int, float)):
        return f"{val:.2f}"
    return str(val)


def summarize(base_url: str) -> str:
    health = fetch_json(f"{base_url}/health")
    ready = fetch_json(f"{base_url}/ready")
    state = fetch_json(f"{base_url}/state")
    comp = fetch_json(f"{base_url}/compliance/status")

    ts = time.strftime("%H:%M:%S")
    ready_ok = bool(ready.get("ok") or ready.get("ready")) and ready.get("http_status") == 200
    lines = [
        f"[{ts}] mode={health.get('mode', '?')} paused={health.get('is_paused', '?')} ready={ready_ok}",
        "  ready: "
        f"leader={ready.get('leader', '?')} "
        f"hb(md/ord/scan)={fmt_number(ready.get('marketdata_heartbeat', '?'))}/"
        f"{fmt_number(ready.get('order_stream_heartbeat', '?'))}/"
        f"{fmt_number(ready.get('scan_heartbeat', '?'))}",
        "  state: "
        f"open={state.get('is_market_open', '?')} "
        f"ws={state.get('websocket_connected', '?')} "
        f"subs={state.get('subscription_count', '?')} "
        f"positions={state.get('positions_count', '?')} trades={state.get('trades_today', '?')}",
        "  compliance: "
        f"static_ip={comp.get('static_ip_msg', comp.get('error', '?'))} | "
        f"oauth={comp.get('oauth_msg', '?')} | "
        f"tops={comp.get('tops_msg', '?')}",
    ]

    alerts = []
    if not ready_ok:
        alerts.append(f"not ready ({ready.get('status', ready.get('http_status'))})")
    if health.get("is_paused") is True:
        alerts.append("trading paused")
    if state.get("websocket_connected") is False:
        alerts.append("websocket disconnected")
    if comp.get("static_ip_ok") is False:
        alerts.append(f"static IP: {comp.get('static_ip_msg')}")
    if comp.get("oauth_ok") is False:
        alerts.append(f"oauth: {comp.get('oauth_msg')}")

    if alerts:
        lines.append("  ⚠️  " + " | ".join(alerts))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Watch paper trading health/compliance.")
    parser.add_argument("--base", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--interval", type=int, default=15, help="Seconds between checks (default: 15)")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit")
    args = parser.parse_args()

    if args.once:
        print(summarize(args.base))
        return

    try:
        while True:
            print(summarize(args.base), flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped watcher.", file=sys.stderr)


if __name__ == "__main__":
    main()
