# Deployment Guide

## Live Signal Consumption

The Foundry produces `results/live_signal.json`. This is an artifact-only output.

To trade this signal:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Use a separate execution script (bridge) to read the JSON and place orders via `packages.core`.

## Gating
The signal is "SKIPPED" if:
- Market is Closed.
- No strategy passes the strict OOS criteria (Sharpe > 1.2, DD < 20%).

## Proxies
We analyze `^NSEI` (Nifty 50 Index) but the signal JSON includes `proxy_symbol_live` (e.g., `NIFTY FUT`) for execution mapping.
