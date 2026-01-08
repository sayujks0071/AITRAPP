# Deployment Guide

## Architecture

The Foundry runs as an autonomous sidecar (GitHub Action or Cron Job). It produces `live_signal.json`.

The Core Execution System (if enabled) reads this JSON and executes orders.

## Safety Gates

1. **Signal Artifact**: Pure JSON. No broker code in Foundry.
2. **Environment**: `ENABLE_LIVE=true` required.
3. **File Lock**: `approvals/ALLOW_LIVE.txt` required.
4. **Market Hours**: Strict session enforcement.

## Consumption

To consume the signal:
1. Parse `results/live_signal.json`.
2. Verify `status == "OK"`.
3. Check `timestamp_ist` is fresh (< 5 mins).
4. Map `signal` (1, -1, 0) to orders.
5. Use `proxy_symbol_live` for execution.
