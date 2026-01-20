# Backtesting Methodology

## Engine
- **Timeframe**: Daily (1D).
- **Execution**: Signal generated at `Close[i]` is executed at `Open[i+1]`.
- **Costs**:
  - Slippage: 5 bps per side.
  - All-in Cost: 10 bps per side (covering Brokerage, STT, Exchange Fees, Stamp Duty).
  - Total Round Trip Drag: ~30 bps.

## Walk-Forward Evaluation
To avoid overfitting, we use Anchored Walk-Forward Evaluation.
- **Folds**: Data is split into 4 OOS folds (default).
- **Training**: Candidates are generated with random parameters (implicit training).
- **Validation**: Performance is measured strictly on the OOS folds.
- **Ranking**: Based on OOS metrics only.

## Metrics
- **CAGR**: Compound Annual Growth Rate.
- **Sharpe Ratio**: Daily Returns / Volatility (Annualized).
- **Calmar Ratio**: CAGR / Max Drawdown.
- **Stability**: Inverse of rolling Sharpe dispersion.
- **Turnover**: Penalized if excessive.

## Ranking Score
Composite score calculated as:
```
Score = 0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - Penalty
```

## Sanity Checks
Candidates are rejected if:
- Total trades < 30 (Insufficient sample).
- Max Drawdown > 35%.
- Fewer than 2 positive OOS folds.
