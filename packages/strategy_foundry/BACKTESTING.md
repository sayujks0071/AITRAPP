# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Data Source**: Yahoo Finance (Adjusted Close? No, using Close).
- **Execution**: Next-Bar Open. Signals are generated on Close[T]. Trade enters on Open[T+1].
- **Costs**:
  - Slippage: 5 bps per side.
  - All-in Fees: 3 bps per side (Tax, Brokerage).
  - Total per round trip: ~16 bps.

## Walk-Forward & Selection
- Strategies are generated with fixed parameters.
- Candidates are evaluated on the full history (10 years).
- **Ranking**:
  - Sharpe Ratio (30%)
  - Calmar Ratio (25%)
  - CAGR (20%)
  - Stability (15%) - Rolling Sharpe Dispersion
  - Turnover (10%) - Penalty for excessive trading

## Live Signals
- The "Champion" strategy is promoted if it beats the incumbent by 10% score improvement.
- Signals are published as JSON only.
- No automatic execution.
