# Deployment & Live Signals

## Philosophy
- **Paper First**: Signals are published as JSON artifacts. No automated execution initially.
- **Safety**: `MarketHoursGuard` ensures signals are only valid during market hours.
- **Gating**: Live signals are only published if the Champion strategy meets strict criteria (Sharpe > 1, DD < 25%).

## Consumption
To consume `live_signal.json`:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Verify `approvals/ALLOW_LIVE.txt` exists.
3. Read JSON, validate `timestamp_ist` is recent (< 5 mins).
4. Verify `status` is "OK".
5. Execute manually or via separate bridge.
