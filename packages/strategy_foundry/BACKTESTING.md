# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Execution**: Signals generated at Close of Day T are executed at Open of Day T+1.
- **Costs**:
  - Slippage: 5 bps per side.
  - Brokerage: 20 INR per order.
  - STT/Taxes: ~3 bps.
- **Liquidity**: Assumed sufficient (Index ETFs/Futures).

## Walk-Forward Evaluation
To avoid overfitting, we use Walk-Forward Validation:
1. Data is split into N folds.
2. We verify the strategy performs well on "Out of Sample" (OOS) data in each fold.
3. Ranking is based *only* on OOS metrics.

## Metrics
- **CAGR**: Compound Annual Growth Rate.
- **Sharpe Ratio**: Risk-adjusted return (rf=0).
- **Max Drawdown**: Peak-to-trough decline.
- **Stability**: Fraction of OOS folds with positive return.

## Sanity Checks
Strategies are rejected if:
- < 30 trades (statistical significance).
- > 35% Max Drawdown.
- Poor OOS stability.
