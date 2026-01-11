# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Execution**: Orders executed at Next Open price.
- **Costs**:
  - Slippage: 5 bps per side.
  - Brokerage: Flat 20 INR.
  - Taxes: 0.03% (STT) turnover.

## Walk-Forward Evaluation
- **Method**: K-Fold split.
- **Training**: None (Random Generation).
- **Validation**: Strategy run on full history, but performance metrics aggregated across folds to ensure stability.
- **OOS**: Technically the entire history is OOS for the specific random parameter set (we do not fit parameters).

## Metrics
- **Sharpe**: Trade-based approximation.
- **Calmar**: CAGR / MaxDD.
- **Stability**: Inverse of Sharpe variance across folds.

## Ranking
Composite Score:
`0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*Turnover`
