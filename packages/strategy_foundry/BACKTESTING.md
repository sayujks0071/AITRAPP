# Backtesting Methodology

## Engine
- **Timeframe**: Daily (1D)
- **Execution**: Next-Day Open. Signals generated on Close of day T are executed at Open of day T+1.
- **Costs**:
  - Slippage: 5 bps per side (10 bps round trip)
  - Brokerage: ~20 Rs per order flat (approximated)
  - Taxes: STT, GST, Stamp Duty included in "All-in" 20 bps estimate or detailed model.

## Walk-Forward Analysis (WFA)
To prevent overfitting, we use Walk-Forward Analysis:
- Data is split into N folds (default 4).
- Expanding Window: Train on Start..T, Test on T..T+k.
- Since strategies are randomly generated (no optimization loop), WFA acts as Cross-Validation over time.
- Metrics (Sharpe, CAGR, Drawdown) are computed on the Out-Of-Sample (OOS) period only.

## Sanity Checks
Strategies are rejected if:
- Total trades < 30 (statistically insignificant)
- Max Drawdown > 35%
- Fewer than 50% of OOS folds are positive.

## Ranking
Score = 30% Sharpe + 25% Calmar + 20% CAGR + 15% Stability.
Stability is the inverse variance of Sharpe across folds.
