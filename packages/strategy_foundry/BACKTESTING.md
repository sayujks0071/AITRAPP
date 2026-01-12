# Backtesting Methodology

## Assumptions

- **Timeframe**: Daily (1D).
- **Execution**: Market Order at Next Bar Open.
- **Costs**:
  - Slippage: 5 bps per side.
  - Commission + Tax: 10 bps per side (conservative estimate).
- **Data**: Yahoo Finance (Close is Adjusted Close? No, using standard Close).

## Walk-Forward Analysis

To prevent overfitting, we use Walk-Forward Validation:
1. **Train** on expanding window (e.g., 2 years).
2. **Test** on subsequent rolling window (e.g., 6 months).
3. **Metrics** are computed strictly on concatenated Test folds (Out-of-Sample).

## Ranking

Composite Score:
- 30% OOS Sharpe
- 25% OOS Calmar
- 20% OOS CAGR
- (Penalties for turnover or instability may apply)

## Sanity Checks

Candidates are rejected if:
- < 10 Trades (Fast Mode) or < 30 Trades (Prod).
- Max Drawdown > 35%.
