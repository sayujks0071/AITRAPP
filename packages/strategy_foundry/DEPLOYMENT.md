# Deployment & Live Signals

**Strategy Foundry is a Research Lab. It does NOT place orders.**

## Signal Artifact

If a Champion is active and the market is open, `live_signal.json` is generated:

```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3...",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "Logic: ema_crossover(10, 50)",
  "status": "OK"
}
```

- `signal`: 1 (Long), -1 (Short), 0 (Flat).
- `status`: "OK" or "SKIPPED".

## Consumption (Optional)

To wire this to execution (NOT RECOMMENDED without audit):

1. **Gating**: Ensure `ENABLE_LIVE=true` in env and `approvals/ALLOW_LIVE.txt` exists.
2. **Bridge**: A separate process must read `live_signal.json`.
3. **Execution**: Map `signal` to `packages.core.execution`.

## Safety

- **Champions** must pass strict gates (Sharpe > 1.0, DD < 25%) to be published.
- **Market Hours** are checked via `packages.core.market_hours`.
- **Fail-safe**: If data is stale or missing, signal is SKIPPED.
