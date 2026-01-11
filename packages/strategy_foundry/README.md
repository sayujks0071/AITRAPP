# Strategy Foundry

An autonomous research lab that generates, backtests, and ranks daily strategies for NIFTY/SENSEX, publishing paper-only signals once strict gates pass.

## Highlights
- **Hourly pipeline** re-downloads Yahoo Finance OHLCV, generates random strategies via a grammar of Trend / Mean Reversion / Volatility blocks, and runs walk-forward backtests.
- **Hybrid engine** reuses `packages/core` adapters for indicators, costs, and market hours while keeping research logic isolated inside `packages/strategy_foundry`.
- **Champion system** persists the incumbent, compares with fresh challengers, and only promotes when Sharpe / drawdown thresholds are beaten.
- **Live artifacts** land in `packages/strategy_foundry/results/live_signal.json` (no auto-execution).

## Layout
- `data/` – cached Yahoo loader with staleness checks.
- `factory/` – grammar blocks (`EmaCross`, `RsiFilter`, `Supertrend`, `Donchian`) + generator.
- `backtest/` – vectorized engine, metrics, sanity filters, walk-forward evaluator.
- `selection/` – ranking + promotion scaffolding.
- `live/` – signal publisher and market-hours guard.

## Running
```bash
# Standard run (full search)
python packages/strategy_foundry/run_hourly.py

# Fast mode for CI / PRs
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

Dependencies are lightweight: `pip install pandas numpy requests structlog pytz`.

## Signal Schema
`results/live_signal.json` (example)
```json
{
  "timestamp_ist": "2026-01-11T10:00:00+05:30",
  "champion_id": "ab123...",
  "instrument": "NIFTY",
  "signal": 1,
  "status": "OK",
  "reason": "OK"
}
```
Signals only publish when markets are open, a champion exists, and gating rules (Sharpe ≥ 1.0, MaxDD ≤ 25%) hold.
