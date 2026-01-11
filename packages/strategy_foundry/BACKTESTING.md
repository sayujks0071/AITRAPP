# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Execution**: Signals on the Close, trades at the next session Open.
- **Costs**:
  - Slippage: 5 bps per side (conservative buffer).
  - Brokerage: Zerodha-like flat 20 INR structure + statutory taxes (~0.03% turnover).

## Data
Daily OHLCV is sourced from Yahoo Finance (`^NSEI`, `^BSESN`). This is sufficient for regime detection, but minor gaps/delays versus broker feeds should be expected.

## Walk-Forward Evaluation
- **Method**: Expanding-window walk-forward (4 folds).
- **Validation**: Strategy metrics aggregated per fold; candidates must be profitable in ≥3 folds to proceed.
- **Training**: There is no traditional fit—parameters come from random grammar sampling, so each configuration is effectively out-of-sample.

## Intraday Constraints
- Flatten positions by 15:20 IST; no overnight carry.
- Optional guardrail: max 1 trade per direction per day.

## Metrics
- **Sharpe**: Trade-based approximation.
- **Calmar**: CAGR / MaxDD.
- **Stability**: Inverse of Sharpe variance across folds.

## Ranking
Composite Score:
`0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*Turnover`
