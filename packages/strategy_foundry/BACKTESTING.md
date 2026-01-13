# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Execution**: Market Order at Next Bar Open.
- **Costs**: 5bps slippage + 3bps fees (approx).
- **Long Only**: Currently restricted to Long/Flat.

## Evaluation
- **Walk-Forward**: Expanding window validation.
- **Metrics**: OOS Sharpe, CAGR, MaxDD.
- **Sanity**: Minimum 30 trades, MaxDD < 35%.

## Ranking
Composite Score:
- 30% Sharpe
- 25% Calmar
- 20% CAGR
- 15% Stability
- -10% Turnover (Penalty)

## Caveats
- Yahoo Finance data may have adjustments/gaps.
- "Next Open" execution assumes liquidity at Open.
