# Deployment & Consumption

## Live Signal
The foundry produces a signal artifact at `packages/strategy_foundry/results/live_signal.json`.

### Schema
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4",
  "timeframe": "1d",
  "instrument": "NIFTY",
  "proxy_symbol_live": "NSE:NIFTY50-FUT",
  "signal": 1, // 1 = LONG, 0 = FLAT
  "status": "OK",
  "reason": "Signal Generated"
}
```

## Consumption
Core execution systems should:
1. Poll `live_signal.json` (or watch for file changes).
2. Verify `timestamp_ist` is fresh (within last 24 hours for Daily strategies).
3. Verify `status` is "OK".
4. execute the target position indicated by `signal`.

## Safety Gates
- **Live Trading Flag**: Must be enabled via `ENABLE_LIVE=true` env var in the consumer.
- **Approval File**: Must exist at `approvals/ALLOW_LIVE.txt`.
- **Market Hours**: Foundry only publishes during market hours.
- **Performance Gates**: Signals are only generated if the Champion strategy meets strict OOS performance criteria (Sharpe > 1.0, Low Drawdown).

<!-- Verified -->
