# Deployment Guide

## Signal Consumption

The Foundry produces a `live_signal.json` artifact.

**Path**: `packages/strategy_foundry/results/live_signal.json`

**Schema**:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4",
  "timeframe": "15m",
  "instrument": "NIFTY",
  "proxy_symbol_live": "NIFTY23OCTFUT",
  "signal": 1,
  "rule_summary": "trend_ema_cross + trailing_stop_atr",
  "risk": {
      "stop": "atr_stop",
      "params": {"multiplier": 2.0},
      "flat_by": "15:25"
  },
  "status": "OK"
}
```

## Gating Requirements

Live execution requires:
1. `ENABLE_LIVE=true` environment variable.
2. `approvals/ALLOW_LIVE.txt` file presence.
3. Successful authentication with Broker.
4. `live_signal.json` status == "OK".

## Paper Trading

To run in paper mode:
1. Ensure `foundry.yaml` has correct paper proxies.
2. Run the hourly job.
3. Consume `live_signal.json` and route to paper simulator.

## Monitoring

- Check GitHub Actions logs for "Strategy Foundry Hourly" workflow.
- Review `leaderboard.md` in artifacts for current champion performance.
