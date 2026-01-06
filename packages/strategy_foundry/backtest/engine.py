import pandas as pd
import numpy as np
from typing import Dict, Any, List

def run_backtest(df: pd.DataFrame, positions: pd.Series, costs: Dict[str, float]) -> Dict[str, Any]:
    """
    Backtest engine.
    df: OHLCV data
    positions: 1 (long), 0 (flat). Series index matches df.
    costs: {'slippage_bps': 5, 'all_in_cost_bps': 3}

    Returns:
       metrics: Dict
       equity_curve: pd.Series
       trades: pd.DataFrame
    """
    # Align
    # Logic: If position[i] != position[i-1], we trade at Open[i+1].
    # So we execute at Next Open.

    # Target positions
    target_pos = positions.shift(1).fillna(0) # Logic: Signal at close i -> Trade at i+1

    # Execution price is Open
    exec_price = df['open']

    # Calculate returns
    # Strategy Return = Position[i-1] * (Close[i] - Close[i-1]) / Close[i-1]
    # BUT we need to account for execution at Open.
    # More precise:
    # If holding from i-1 to i: Return is (Open[i] - Open[i-1]) / Open[i-1] ???
    # No, typically daily backtest uses Close-to-Close or Open-to-Open.
    # Standard "Next Open" method:
    # We enter at Open[i]. We hold until Open[j].
    # Daily PnL:
    # Day i (Entry): (Close[i] - Open[i]) / Open[i]
    # Day k (Holding): (Close[k] - Close[k-1]) / Close[k-1]
    # Day j (Exit): (Open[j] - Close[j-1]) / Close[j-1]

    # Let's use a simpler vectorized approach approximating Close-to-Close returns,
    # adjusted for trade costs at transitions.

    # Market Returns (Close to Close)
    mkt_ret = df['close'].pct_change().fillna(0)

    # Strategy Returns (Gross)
    # If we hold at end of i-1, we get return of i.
    # positions[i] indicates if we want to hold AFTER close of i (for next day).
    # Wait, my generate_positions logic was: "positions[i] = 1" means "we are in position at step i".
    # And the loop logic checked limits at step i.
    # So positions[i] represents state at END of day i.

    # So if positions[i-1] == 1, we are exposed to Day i price action.
    strat_ret = positions.shift(1).fillna(0) * mkt_ret

    # Costs
    # Trades occur when position changes
    # change[i] = positions[i] - positions[i-1]
    # If change != 0, we pay cost.
    # Cost is applied on turnover.
    # Cost bps = slippage + fees
    total_cost_bps = costs.get('slippage_bps', 5) + costs.get('all_in_cost_bps', 3)
    cost_pct = total_cost_bps / 10000.0

    # Turnover is abs(change)
    # But wait, logic above says "Signal at i -> Trade at Open i+1".
    # So if positions[i] != positions[i-1], we trade at Open[i+1].
    # This means the cost occurs at i+1.
    # However, the return calculation `positions.shift(1) * mkt_ret` uses Close-to-Close.
    # This implies we are fully invested from Close[i-1] to Close[i].
    # This contradicts "Trade at Open".

    # Let's refine for "Trade at Open".
    # If positions[i-1] != positions[i-2], we traded at Open[i].
    # So Day i return is split:
    #   Part 1: Open[i] to Close[i] (if positions[i-1] == 1)
    #   But what about Close[i-1] to Open[i]? That gap belongs to previous state?
    #   Usually:
    #   If pos[i-2]=0, pos[i-1]=1 -> Enter at Open[i].
    #   Return on Day i: (Close[i] - Open[i]) / Open[i].
    #   If pos[i-2]=1, pos[i-1]=1 -> Hold.
    #   Return on Day i: (Close[i] - Close[i-1]) / Close[i-1].

    # This "Trade at Open" logic is hard to fully vectorise perfectly with simple pct_change.
    # But let's try.

    # Open Returns: (Close - Open) / Open
    # Gap Returns: (Open - PrevClose) / PrevClose

    op_ret = (df['close'] - df['open']) / df['open']
    gap_ret = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)

    # State at start of day i comes from decision at i-1
    # pos_intended = positions.shift(1)

    # State at PREVIOUS day (i-1) comes from decision at i-2
    # prev_pos = positions.shift(2)

    # Actual Return on Day i:
    # If prev_pos == pos_intended:
    #    We held through gap.
    #    Ret = GapRet + (1+GapRet)*OpRet = (Close[i]/Close[i-1]) - 1. (Standard Close-Close)
    # If prev_pos != pos_intended:
    #    We traded at Open.
    #    We did NOT participate in Gap (assuming we were flat, or gap was for prev pos).
    #    Wait, if we were Long and switch to Flat:
    #      We sell at Open. We get Gap return. Then flat for OpRet.
    #    If we were Flat and switch to Long:
    #      We buy at Open. We miss Gap return. We get OpRet.

    pos_prev = positions.shift(2).fillna(0) # State entering the gap
    pos_curr = positions.shift(1).fillna(0) # State desired for the day

    # Returns from Gap
    r_gap = pos_prev * gap_ret

    # Returns from Session
    r_session = pos_curr * op_ret

    # Total Day Return approx = r_gap + r_session
    # (ignoring compounding within the day for simplicity, or use (1+r)*(1+r)-1)
    # Correct compounding: (1 + r_gap) * (1 + r_session) - 1
    # But wait, if pos changed, r_gap applies to OLD pos, r_session applies to NEW pos.

    day_ret = (1 + r_gap) * (1 + r_session) - 1

    # Costs
    # We trade if pos_curr != pos_prev
    turnover = (pos_curr - pos_prev).abs()
    costs_series = turnover * cost_pct

    net_ret = day_ret - costs_series

    # Equity Curve
    equity_curve = (1 + net_ret).cumprod()

    # Drawdown
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak

    # Trades list
    trades = []
    # Identify trade points
    trades_mask = turnover > 0
    trade_indices = df.index[trades_mask]

    # This is a quick approximation. For detailed trade list (entry price, exit price),
    # we need to iterate.
    # Since we need "trades table", let's reconstruct it.

    in_trade = False
    entry_date = None
    entry_price = 0.0

    # Scan for trades
    # Using the pos_curr series which represents holding status during the day
    p = pos_curr.values
    dates = df.index
    opens = df['open'].values
    closes = df['close'].values

    # Reuse loop or just use the changes
    # transitions: 0->1 (Buy at Open), 1->0 (Sell at Open)

    for i in range(len(p)):
        if i == 0: continue

        # Buy
        if p[i] == 1 and p[i-1] == 0:
            entry_date = dates[i]
            entry_price = opens[i] # Trade at Open
            in_trade = True

        # Sell
        elif p[i] == 0 and p[i-1] == 1:
            if in_trade:
                exit_date = dates[i]
                exit_price = opens[i] # Trade at Open
                pnl = (exit_price - entry_price) / entry_price
                pnl -= (cost_pct * 2) # Entry + Exit cost

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "return": pnl, # alias
                    "bars": (exit_date - entry_date).days # rough
                })
                in_trade = False

    # Close open trade at end
    if in_trade:
        exit_date = dates[-1]
        exit_price = closes[-1]
        pnl = (exit_price - entry_price) / entry_price
        pnl -= (cost_pct * 2)
        trades.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "return": pnl,
            "bars": (exit_date - entry_date).days,
            "status": "OPEN"
        })

    return {
        "equity_curve": equity_curve,
        "drawdown": drawdown,
        "trades": pd.DataFrame(trades),
        "returns": net_ret
    }
