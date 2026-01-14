# Backtesting Methodology

## Engine
- **Timeframe**: Daily (1D).
- **Execution**: Signal generated at Close (t), Entry at Open (t+1).
- **Type**: Vectorized with loop-based risk overlay.
- **Costs**:
  - Slippage: 5 bps (default).
  - Fees: Estimated brokerage + taxes (STT, GST, etc.) via `core` adapter.

## Walk-Forward Evaluation
- The dataset is split into `N` folds (Default 3).
- Strategies are evaluated on each fold.
- Ranking uses the aggregate metrics across folds.
- **Anti-Overfitting**:
  - Strategies are randomly generated (no parameter optimization on In-Sample data).
  - Selection is based on stability across folds.
  - Champions must beat incumbents by significant margin (10% score or 5% MaxDD).

## Metrics
- **Sharpe Ratio**: Risk-adjusted return (rf=0).
- **Calmar Ratio**: CAGR / MaxDD.
- **Stability**: Inverse of Sharpe standard deviation across folds.
- **Sanity Checks**:
  - Min Trades: 30
  - Max DD: 35%

## Caveats
- Yahoo Finance data may have gaps or adjustments.
- Daily timeframe ignores intraday volatility (though Risk Overlay checks Low/High for stops).
- "Next Open" execution assumes liquidity at Open price.
