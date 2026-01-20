# Deployment & Live Signals

## Philosophy
Strategy Foundry is a "Paper First" environment. It **never** places orders directly. It only produces artifacts.

## Signal Artifact
The live signal is published to `packages/strategy_foundry/results/live_signal.json`.

### Schema
```json
{
  "timestamp_ist": "2023-10-27T09:15:00",
  "champion_id": "1a2b3c4d",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "EMA_CROSS -> ENTRY Signal",
  "risk": { "type": "ATR", "params": {...} },
  "status": "OK"
}
```
- `signal`: 1 (Long), 0 (Flat/Exit).
- `status`: "OK" or "SKIPPED".

## Consumption (Bridge)
To trade these signals live:
1. Enable `ENABLE_LIVE=true` in your execution environment.
2. Create approval file `approvals/ALLOW_LIVE.txt`.
3. Implement a reader in `packages/core` that polls `live_signal.json`.
4. Ensure the reader validates the timestamp (freshness) and `status == "OK"`.

**Note**: The default `packages/core` does NOT contain this wiring. It must be added explicitly by the user.

## Gating
Signals are only published if:
- Market is Open (or Pre-open).
- A Champion exists.
- The Champion is "Live Eligible" (High OOS Sharpe, Low DD).
