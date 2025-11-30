#!/usr/bin/env python3
"""
Market session supervisor for Kite-based trader.

Why: Twisted/KiteTicker reactors can't be restarted in-process. We wrap the
entire trading stack in a child process and respawn daily during market hours,
optionally refreshing the Kite access token before each start.

Usage:
  python3 scripts/ticker_supervisor.py

Config (env):
  MARKET_START_HHMM=09:05   # session start (local time HH:MM)
  MARKET_END_HHMM=15:40     # session end (local time HH:MM)
  SUPERVISOR_POLL_SECONDS=15
  TOKEN_REFRESH_CMD="python3 scripts/kite_headless_login.py"
  UVICORN_CMD="python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"
"""
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, time as dtime

from dotenv import load_dotenv


def _parse_hhmm(value: str, default: dtime) -> dtime:
    try:
        hh, mm = value.split(":")
        return dtime(int(hh), int(mm), 0)
    except Exception:
        return default


def _refresh_token_if_configured() -> None:
    """Optionally run a token refresh command before market open."""
    cmd = os.getenv("TOKEN_REFRESH_CMD")
    if not cmd:
        return
    try:
        subprocess.run(cmd, shell=True, check=True, timeout=180)
    except Exception as exc:
        print(f"[supervisor] Token refresh command failed: {exc}", file=sys.stderr)


def _spawn_worker(cmd: str) -> subprocess.Popen:
    """Spawn the trading process."""
    env = os.environ.copy()
    return subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, env=env)


def _stop_worker(proc: subprocess.Popen) -> None:
    """Stop the trading process gracefully, escalating if needed."""
    if proc and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=10)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass


def main() -> None:
    load_dotenv()

    start_time = _parse_hhmm(os.getenv("MARKET_START_HHMM", "09:05"), dtime(9, 5))
    end_time = _parse_hhmm(os.getenv("MARKET_END_HHMM", "15:40"), dtime(15, 40))
    poll = int(os.getenv("SUPERVISOR_POLL_SECONDS", "15"))
    worker_cmd = os.getenv(
        "UVICORN_CMD",
        "python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000",
    )

    proc: subprocess.Popen | None = None
    is_running = False

    print(f"[supervisor] Running with start={start_time}, end={end_time}, poll={poll}s")
    try:
        while True:
            now = datetime.now()
            weekday = now.weekday()  # 0=Mon
            in_session = (weekday < 5) and (start_time <= now.time() <= end_time)

            if in_session:
                if not is_running or (proc and proc.poll() is not None):
                    if proc and proc.poll() is not None:
                        print("[supervisor] Worker crashed; restarting.")
                    print("[supervisor] Market open: starting worker.")
                    _refresh_token_if_configured()
                    proc = _spawn_worker(worker_cmd)
                    is_running = True
            else:
                if is_running and proc:
                    print("[supervisor] Market closed: stopping worker.")
                    _stop_worker(proc)
                    is_running = False
                    proc = None

            time.sleep(poll)
    except KeyboardInterrupt:
        if proc:
            _stop_worker(proc)
        print("[supervisor] Exit on keyboard interrupt.")
        sys.exit(0)


if __name__ == "__main__":
    main()
