# Deployment & Live Signals

## Philosophy

Strategy Foundry is **Passive**. It generates signals but does not execute them.
Live execution requires a separate, explicit bridge in `packages/core` which is currently **Disabled**.

## Signal Artifact

The output is `packages/strategy_foundry/results/live_signal.json`.

```json
{
  "timestamp_ist": "2023-10-27T09:15:00",
  "champion_id": "abc123hash",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "Trend(EMA) + Exit(ATR)",
  "status": "OK"
}
```

## Gating

To enable any form of live usage (future):
1. Env var `ENABLE_LIVE=true`
2. File `approvals/ALLOW_LIVE.txt` must exist.
3. Core system must implement a reader for this JSON.

Currently, **NO** order placement code exists in this module.
