# Deployment Guide

## Philosophy
- **Paper First**: Foundry only writes JSON artifacts; order execution stays off-box.
- **Safety Rails**: Market-hour guard plus manual approvals prevent accidental live flips.
- **Meritocracy**: Only champions beating gating thresholds (Sharpe ≥ 1.0, MaxDD ≤ 25%) may publish actionable signals.

## Live Signal Consumption
The runner writes `packages/strategy_foundry/results/live_signal.json`. To consume it:
1. Set `ENABLE_LIVE=true` and ensure `approvals/ALLOW_LIVE.txt` exists. Without both, `run_hourly.py` will skip publishing.
2. Read the JSON, verify `status == "OK"` and `timestamp_ist` is fresh (<5 minutes).
3. Map the `instrument` to your execution proxy (e.g., `NIFTY` → broker-specific symbol) in the downstream bridge.
4. Execute manually or via a separate, audited bridge that talks to `packages.core`.

## Gating & Failure Modes
- **Market Closed** → status `SKIPPED`, reason `Market Closed`.
- **No Champion / Not Eligible** → status `SKIPPED`, explicit reason.
- **Champion Health** → requires Sharpe ≥ 1.0 and Max Drawdown ≤ 25% (configurable in code).
- **Approvals Disabled** → status `SKIPPED`, reason `Live Disabled`.

Downstream systems should treat any non-`OK` status as non-tradable.

## Operational Notes
- Signals are generated off the prior completed daily bar to avoid repaint.
- Artifacts live under `packages/strategy_foundry/results/` so runners/cron can archive them easily.
- Keep `approvals/ALLOW_LIVE.txt` under change-control; deleting the file is the fastest kill switch.
