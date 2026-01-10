# Deployment & Live Gating

## Live Signal

The system publishes `live_signal.json` only when:
1. Market is OPEN.
2. A Champion exists and is "Live Eligible" (verified by WFA).

## Consumption

To trade this signal:
1. Enable `ENABLE_LIVE=true` in environment.
2. Create `approvals/ALLOW_LIVE.txt` on the trading server.
3. Use a bridge (not provided by default) to read `live_signal.json` and place orders.

**Safety First**: The Foundry intentionally **does not** execute orders. It only produces research artifacts.
