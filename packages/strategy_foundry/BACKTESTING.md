# Backtesting Methodology

## Data Strategy
- **Primary**: 5m and 15m Intraday bars.
- **Sanity**: 1D bars.
- **Source**: Yahoo Finance (unofficial) via `requests`.
- **Cache**: CSV files in `data/cache/`.

## Execution Model
- **Signal**: Calculated on Bar Close (i).
- **Execution**: Assumed at Open of next Bar (i+1).
- **Session**: Entries allowed 09:15-15:20 IST. Forced exit at 15:25 IST.
- **Costs**:
  - Brokerage + Tax: ~3 bps/side.
  - Slippage: 2 bps/side.
  - Spread Guard: 1 bps/side.

## Validation (Walk-Forward)
- **Folds**: 4 folds for robustness.
- **OOS**: Only Out-of-Sample performance is used for ranking.
- **Rejection**: Strategies with < 3/4 positive folds or high drawdown (>30%) are rejected.

## Sanity Checks
- **1D Sanity**: Top candidates are checked on Daily timeframe. If performance is catastrophically bad (Sharpe < -0.2), they are penalized/rejected.
- **Overfit Checks**: Penalties for "end-of-day" lucky profits or excessive turnover.
