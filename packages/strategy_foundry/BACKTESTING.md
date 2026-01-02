# Backtesting Methodology

## Engine

- **Timeframe:** Daily (1D)
- **Execution:** Orders are executed at the Open of the NEXT bar after the signal is generated.
- **Costs:**
  - Slippage: 5 bps per side.
  - All-in Cost: 10 bps per side (brokerage + taxes).
- **Position:** Long-only (currently).

## Walk-Forward Evaluation

To prevent overfitting, we use Walk-Forward Evaluation.
- **Splits:** 3 folds (default) or 2 folds (FAST_MODE).
- **Process:**
  - The strategy (with fixed params) is evaluated on distinct time chunks (OOS).
  - Metrics are aggregated across these OOS chunks.
- **Selection:** Strategies are ranked based on OOS performance only.

## Ranking Score

The composite score is calculated as:
- 30% OOS Sharpe Ratio
- 25% OOS Calmar Ratio
- 20% OOS CAGR
- 15% Stability (inverse of Sharpe dispersion)

## Sanity Checks

Strategies are rejected if:
- Max Drawdown > 35%
- Positive Folds < 2 (in normal mode)
