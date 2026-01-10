# Backtesting Methodology

## Assumptions
- **Execution**: Signal on close, trade on next open.
- **Costs**:
  - Slippage: 5bps
  - Brokerage: min(20, 0.03%)
  - Taxes: ~3bps (STT + Exchange + GST)
- **Intraday**:
  - Positions must be flat by 15:25 IST.
  - No carry over.

## Evaluation
- **Walk-Forward**: Data is split into 4 folds. Strategies are evaluated on each fold to measure consistency.
- **Ranking**: Blended score of Sharpe, Calmar, CAGR, Stability, and Turnover.
- **Sanity Checks**:
  - Minimum trades per period.
  - Max drawdown limits.
  - Daily sanity check (1D timeframe) to ensure robustness against noise.

## Limitations
- **Data**: Yahoo Finance data is used (via `requests`). Intraday history is limited (~60 days).
- **Fills**: Assumes perfect fills at Open for entries. Stop losses are checked against High/Low.
