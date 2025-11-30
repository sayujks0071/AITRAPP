# MCX Live Runbook (v1)

Use after completing paper/soak tests. Keep first live size tiny (1 lot) and monitor constantly.

## Pre-Open Checklist (14:30–14:50 IST)
- Creds/env: `KITE_API_KEY/SECRET/ACCESS_TOKEN`, `APP_MODE=LIVE`, `APP_CONFIG=configs/mcx_live.yaml`, `EXPECTED_EGRESS_IP`.
- Kill switch: ensure off; heartbeat OK.
- Config sanity: mcx_live.yaml `dry_run:false`, `mcx_product` correct for broker, freeze_limits set.
- Symbols: CRUDEOIL, GOLDM, SILVERM only. Options disabled (`mcx_include_options:false`).
- Logs/metrics: log file path writable, Prometheus port free.

## Start (14:50–15:00 IST)
- Launch: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000`.
- Verify: instrument sync success; MCX contracts selected; bars ticking; indicators populated.
- Strategies: keep disabled initially; enable one at a time after data sanity checks.

## Entry Window (post 15:00 through evening)
- Confirm `_is_market_open` true in MCX window (09:00–23:30).
- Watch liquidity guard hits (spread/volume); expect some rejects in thin tape.
- If enabling a strategy: start with `PremiumAdaptiveTrend` (futures only), size=1 lot.

## Execution Checks
- Dry-run is false; confirm order logs show `exchange=MCX`, qty rounded to lot, product=NRML.
- Limit chaser: if used, pass `meta={'exchange':'MCX'}`; verify placements/mods route MCX.
- Freeze: orders sliced under per-symbol freeze_limits; no rejects expected.

## Monitoring
- Tails: `tail -f logs/mcx_live.log | rg MCX`.
- Metrics: Prometheus on 9090; watch heartbeats, order errors, rate-limit alerts.
- Liquidity guard: investigate repeated spread/volume rejects (may need wider thresholds at night).

## Incident Handling
- Kill switch on any anomaly; check cancel of open orders.
- Token errors: refresh access token immediately; rerun service.
- Spread blowout: disable strategies, keep data running, reassess thresholds.

## EOD / Session Close
- Auto squareoff at `mcx_eod_squareoff_time` (23:20). Verify flatten logs.
- Manual contingency: use broker terminal to flatten if auto fails.

## Post-Close
- Validate positions=0, PnL captured, logs archived.
- Rotate access token if needed; reset kill switch for next day.

## Next Tests
- Dual-session paper soak (NSE + MCX) over an evening.
- Enable MCX options only after futures flow is stable and liquidity filters are tuned.
