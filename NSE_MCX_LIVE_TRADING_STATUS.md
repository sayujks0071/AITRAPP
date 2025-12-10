# NSE vs MCX Live Trading Status (March 2025)

## NSE — Live-Ready
- Live configs: `configs/kite_day1_live.yaml`, `configs/kite_canary_live.yaml`.
- Components validated: execution engine, risk, compliance, strategies, allocator wiring, market data, EOD squareoff, logging/monitoring.
- State: Ready for live after final paper soak; use existing day-1 live runbooks.

## MCX — Partial (Paper-Ready, not Live-Ready)
- What exists:
  - Instrument fetch includes MCX; universe builder can select MCX futures (options gated via config).
  - MCX session hours and EOD squareoff in `market` config.
  - Execution engine routes by exchange, enforces tick/lot, MCX product override; limit-chaser exchange-aware.
  - Risk: MCX fees/slippage overrides; MCX tick-distance guard; spread/volume liquidity guard (NSE/MCX-aware).
  - NEW: `configs/mcx_live.yaml` (LIVE, futures-only, conservative sizing, dry_run=false, freeze_limits set).
  - NEW: `MCX_LIVE_RUNBOOK.md` for go-live procedure.
- Missing for LIVE:
  1) Market data streaming validation for MCX instruments (ticks→bars→indicators).
  2) MCX order execution test (paper/live sandbox) with exchange/product settings.
  3) Pre-live gate/validation checklist specific to MCX (fees/taxes, product codes, freeze qty).
  4) Dual-session (NSE+MCX) paper test covering open/close windows and EOD squareoff.

## Priority Actions to Complete MCX Live
1) Market data paper test: subscribe MCX symbols, confirm bars/indicators populate, liquidity guard fires when spread/volume fail.
2) Execution paper test: place small paper orders via `place_order` with MCX instrument; verify tick/lot and product routing; test limit-chaser with `meta={'exchange': 'MCX'}`.
3) Pre-live MCX gate: freeze qty/product mapping, fees/taxes, brokerage codes, kill-switch check, EOD squareoff at MCX time.
4) Dual-session soak (NSE + MCX) in PAPER over one evening session.

## Quick Reference (Current Defaults)
- MCX session: 09:00–23:30, squareoff 23:20 (configurable).
- MCX risk overrides (defaults): slippage 8 bps, fees 30/order, 30/option leg.
- Liquidity guard: NSE spread ≤0.8% & volume ≥100; MCX spread ≤1.2% & volume ≥50 (uses features or bid/ask fallback).
- Product default: `mcx_product: NRML` (override per broker if required).


