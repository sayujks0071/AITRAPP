# Backtesting Methodology

## Philosophy
We prioritize robustness over curve-fitting.
1. **No Optimization**: Parameters are randomly generated and fixed. We select *stable* random candidates, we do not "optimize" parameters on a single candidate.
2. **Walk-Forward**: We split history into folds. Candidates must perform well across folds.
3. **Complexity Penalty**: We limit the number of blocks and parameters.

## Engine
- **Timeframe**: Daily (1D).
- **Execution**: Open of Next Bar.
- **Costs**:
  - Slippage: 5 bps
  - Brokerage: Flat Rs 20
  - Taxes: Approx 3 bps (STT + others)

## Metrics
- **Risk-Adjusted**: Sharpe, Sortino, Calmar.
- **Absolute**: CAGR, Max Drawdown.
- **Stability**: Volatility of returns, Consistency across folds.

## Ranking
Composite Score:
- 30% Sharpe (Out-of-Sample)
- 25% Calmar
- 20% CAGR
- 15% Stability
- -10% Turnover Penalty

## Promotion Gates
To become a Champion:
- Sharpe >= 1.0
- Max Drawdown <= 25% (i.e. > -0.25)
- Positive performance in >= 3 folds (OOS)
- Score must exceed current champion by 10% OR significantly improve Drawdown.
