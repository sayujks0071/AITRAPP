# Backtesting Methodology

## Assumptions
- **Timeframe:** Daily Bars (1D).
- **Execution:** Next Bar Open. Signals generated on Close[t] are executed at Open[t+1].
- **Data:** Adjusted Close data from Yahoo Finance, localized to Asia/Kolkata.

## Costs
- **Commission:** Configurable bps (default 5 bps).
- **Slippage:** Configurable bps (default 2 bps).
- Costs are applied to the full transaction value on every trade.

## Validation
- **Walk-Forward:** Data is split into 5 folds.
- **Sanity Checks:**
  - Minimum 30 trades.
  - Max Drawdown < 35%.
  - Must have positive returns in > 3/5 folds for promotion.

## Metrics
- **CAGR:** Compound Annual Growth Rate.
- **Sharpe:** Risk-adjusted return (Rf=5%).
- **MaxDD:** Maximum Peak-to-Valley Drawdown.
- **Stability:** Consistency across Walk-Forward folds.
