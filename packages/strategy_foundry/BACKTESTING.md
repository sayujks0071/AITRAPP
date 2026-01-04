# Backtesting Details

## Data Assumptions
- Intraday data (5m, 15m) is fetched via Yahoo Finance proxy (e.g. ^NSEI) if not available in Core.
- Timestamps are normalized to Asia/Kolkata.
- Session boundaries: 09:15 - 15:30 IST.

## Costs
- All-in cost: 3 bps per side (covers Brokerage + STT).
- Slippage: 2 bps per side.
- Spread guard: 2 bps penalty.

## Intraday Constraints
- All positions must be flat by 15:25 IST.
- Logic enforces this by checking timestamp time.

## Evaluation
- Walk-forward OOS is approximated by Train/Test split for MVP.
- Metrics calculated on OOS data.
- 1D Sanity check runs top candidates on Daily data to ensure no catastrophic failure.
