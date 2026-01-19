# Backtesting Methodology

## Engine
- **Timeframe**: Daily (1D).
- **Execution**: Orders are generated at Close (signal) and executed at the **Next Open**.
- **Costs**:
  - **Slippage**: 5 bps per side.
  - **Fees**: Estimated using `packages.core.risk` models (STT, Exchange Txn, GST, SEBI).
  - **Rebalancing**: Position changes trigger costs on the delta quantity.

## Walk-Forward Analysis (WFA)
To prevent overfitting, strategies are evaluated using Walk-Forward Analysis.
- Data is split into N folds (default 3).
- Strategies are "trained" (evaluated) on historical segments and validated on Out-Of-Sample (OOS) segments.
- Ranking is based **strictly** on OOS metrics.

## Metrics
- **CAGR**: Compound Annual Growth Rate.
- **Sharpe Ratio**: Risk-adjusted return (Rf=0).
- **Calmar Ratio**: CAGR / Max Drawdown.
- **Stability**: Inverse of rolling Sharpe dispersion.

## Sanity Checks
Strategies must pass sanity checks to be considered:
- **Min Trades**: Must generate sufficient trade frequency (default 30).
- **Max Drawdown**: Must not exceed 35% drawdown.
- **Consistency**: Must be profitable in at least 2 OOS folds.

*Note: In FAST_MODE, these checks are relaxed.*
