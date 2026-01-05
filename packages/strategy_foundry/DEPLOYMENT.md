# Deployment Guide

## Live Signal Consumption

The foundry **does not** execute trades. It produces a signal artifact:

`packages/strategy_foundry/results/live_signal.json`

### Schema
```json
{
  "timestamp_ist": "2023-10-27T10:15:00+05:30",
  "champion_id": "a1b2c3...",
  "timeframe": "5m",
  "instrument": "NIFTY",
  "proxy_symbol_live": "NIFTY 50",
  "signal": 1,
  "status": "OK"
}
```

-   `signal`: `1` (Buy), `-1` (Sell), `0` (Neutral).
-   `status`: `OK` or `SKIPPED`.

### Gating
Live execution requires:
1.  `ENABLE_LIVE=true` environment variable.
2.  `approvals/ALLOW_LIVE.txt` file presence.
3.  Core system kill-switches inactive.

## Paper Trading
To run in paper mode:
1.  Ensure `instrument_map.yaml` has correct `paper_proxy` symbols.
2.  Consume the JSON and route to a paper broker account.
