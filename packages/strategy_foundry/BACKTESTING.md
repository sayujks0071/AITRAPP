# Backtesting Methodology

## Data Handling
- **Sources**: Primary source is Yahoo Finance (via `yfinance` compatible API or direct requests). Fallback mechanisms are in place.
- **Timeframes**: 5m and 15m for intraday. 1D for sanity checks.
- **Caching**: Data is cached in CSV format in `packages/strategy_foundry/data/cache`.

## Execution Simulation
- **Assumptions**:
  - Signals generated on Bar Close.
  - Execution at Next Bar Open.
  - No lookahead bias.
- **Costs**:
  - Commission: 3 bps per side.
  - Slippage: 2 bps per side.
- **Session**:
  - Positions forced flat at 15:25 IST.
  - Trading only during market hours (09:15 - 15:30 IST).

## Evaluation
- **Walk-Forward**: Strategies are evaluated on Out-of-Sample (OOS) data.
- **Metrics**: Sharpe Ratio, Maximum Drawdown, Win Rate, Profit Factor.
- **Sanity Checks**:
  - Minimum trade count to ensure statistical significance.
  - Overfitting checks via stability across folds (planned).
