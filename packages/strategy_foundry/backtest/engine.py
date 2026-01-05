"""
Strategy Foundry - Backtest Engine.
Vectorized execution for speed.
Long-only default.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.adapters.core_indicators import calculate_all
from packages.strategy_foundry.adapters.core_costs import get_default_cost_model
from packages.strategy_foundry.factory.grammar import summarize_rules

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0):
        self.raw_data = data
        self.data = calculate_all(data)
        self.capital = initial_capital
        self.cost_model = get_default_cost_model()

    def run(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run backtest for a single strategy.
        """
        df = self.data.copy()
        blocks = strategy_config.get("blocks", [])

        # 1. Generate Signals
        # 0 = Neutral, 1 = Long Entry, -1 = Exit (for Long Only)
        # We process entry rules first

        entry_signal = pd.Series(False, index=df.index)

        # Apply Filters
        filter_mask = pd.Series(True, index=df.index)

        for block in blocks:
            if block["type"] == "FILTER":
                if block["subtype"] == "ADX_FILTER":
                    thresh = block["params"]["threshold"]
                    filter_mask &= (df["adx_14"] > thresh)

        # Apply Entries
        for block in blocks:
            if block["type"] == "ENTRY":
                if block["subtype"] == "EMA_CROSS":
                    fast = block["params"]["fast"]
                    slow = block["params"]["slow"]
                    # Entry when fast crosses above slow
                    # Use provided EMA columns if standard, or compute
                    # We precomputed some, but grammar might generate others.
                    # For performance, we should ideally restrict grammar to precomputed.
                    # Or compute on fly.
                    # Let's map approximate standard precomputed ones or fail gracefully/compute.
                    # Grammar uses 5, 10, ...
                    # Adapters computed specific ones.
                    # To be robust, let's just recompute specific EMAs needed if not in df.
                    f_col = f"ema_{fast}"
                    s_col = f"ema_{slow}"
                    if f_col not in df.columns:
                        df[f_col] = df["close"].ewm(span=fast, adjust=False).mean()
                    if s_col not in df.columns:
                        df[s_col] = df["close"].ewm(span=slow, adjust=False).mean()

                    cross_up = (df[f_col] > df[s_col]) & (df[f_col].shift(1) <= df[s_col].shift(1))
                    entry_signal |= cross_up

                elif block["subtype"] == "DONCHIAN_BREAKOUT":
                    # Breakout above upper channel
                    # Note: Donchian in adapter is generic 20. Grammar is flexible.
                    p = block["params"]["period"]
                    u_col = f"dc_upper_{p}"
                    if u_col not in df.columns:
                        df[u_col] = df["high"].rolling(window=p).max().shift(1) # Shift 1 so we compare today's high to prev N days high?
                        # Standard Donchian Breakout: Close > Prev N days High (or High > Prev N days High)
                        # Let's use Close > Prev High

                    breakout = df["close"] > df[u_col]
                    entry_signal |= breakout

                elif block["subtype"] == "RSI_REVERSION":
                    # Buy when RSI < lower
                    p = block["params"]["period"]
                    lower = block["params"]["lower"]
                    r_col = f"rsi_{p}"
                    if r_col not in df.columns: # Should be rsi_14
                         # Simplified: if period is 14, use precomputed
                         if p == 14:
                             r_col = "rsi_14"
                         else:
                             # compute
                             pass # TODO implement generic calculation if needed

                    if r_col in df.columns:
                        entry_signal |= (df[r_col] < lower)

        # Combine Entry and Filter
        entry_signal = entry_signal & filter_mask

        # 2. Simulate Execution (Event Loop for correct path dependence of Exits)
        # Vectorized is hard with stateful exits (ATR trailing, Time stop).
        # We will use a fast loop.

        position = 0 # 0 or 1 (Long only)
        entry_price = 0.0
        entry_idx = 0

        trades = []
        equity_curve = [self.capital]

        # Pre-calculate ATR/stops parameters if needed
        # We need generic way to handle multiple exits.

        # Parse Exit Rules
        atr_stop_mult = None
        time_stop_days = None

        for block in blocks:
            if block["type"] == "EXIT":
                if block["subtype"] == "ATR_STOP":
                    atr_stop_mult = block["params"]["multiplier"]
                elif block["subtype"] == "TIME_STOP":
                    time_stop_days = block["params"]["days"]

        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        dates = df.index
        atrs = df["atr_14"].values # Assuming standard ATR 14 for stops

        current_equity = self.capital

        # Iteration
        # We assume execution at NEXT OPEN after signal.
        # So if signal at i, we enter at i+1 open.

        pending_entry = False

        for i in range(1, len(df)):
            price = opens[i]
            dt = dates[i]

            # Check Exit if in position
            if position == 1:
                exit_triggered = False
                exit_reason = ""

                # Check Stops (against today's Open? Or High/Low? conservative: Open or Low)
                # If we gap down below stop, we exit at Open.
                # If we hit stop intraday, we exit at Stop Price (slippage applies).
                # Simplified: Check Low.

                # 1. ATR Stop
                if atr_stop_mult:
                    # Trailing stop or fixed? "ATR stop" usually implies trailing or fixed from entry.
                    # Let's implement Fixed from Entry for simplicity or Trailing.
                    # Grammar just said "ATR Stop". Let's do Trailing from High water mark?
                    # Or simple Fixed Stop Loss: Entry - ATR * Mult.
                    # Let's do Fixed Stop from Entry Price for robustness.
                    stop_price = entry_price - (atrs[entry_idx] * atr_stop_mult)

                    if lows[i] < stop_price:
                        # Stopped out
                        exit_price = min(opens[i], stop_price) # If open is below stop, we execute at open (gap).
                        exit_triggered = True
                        exit_reason = "ATR_STOP"

                # 2. Time Stop
                if not exit_triggered and time_stop_days:
                    days_held = (dt - dates[entry_idx]).days
                    # Or bars held? usually bars.
                    bars_held = i - entry_idx
                    if bars_held >= time_stop_days:
                        exit_price = opens[i]
                        exit_triggered = True
                        exit_reason = "TIME_STOP"

                # 3. Standard Strategy Exit (Opposite Signal)?
                # The grammar defines Exits explicitly.
                # RSI Reversion might have "Sell when RSI > upper" logic?
                # Grammar didn't specify explicit "Profit Target" or "Sell Signal" other than stops.
                # Wait, Mean Reversion usually needs an exit condition (like RSI > Upper).
                # Let's check if there is an RSI_REVERSION block, maybe it implies exit at Upper?
                # The grammar `mean_rev_rsi` has "upper".
                # Let's handle implicit exits.
                for block in blocks:
                     if block.get("subtype") == "RSI_REVERSION":
                         lower = block["params"]["lower"]
                         upper = block["params"]["upper"]
                         p = block["params"]["period"]
                         # If RSI > upper, exit
                         # using close of PREVIOUS bar to decide to exit at OPEN of CURRENT bar
                         if i > 0:
                             prev_rsi = df[f"rsi_{p}" if f"rsi_{p}" in df else "rsi_14"].iloc[i-1]
                             if prev_rsi > upper:
                                 exit_price = opens[i]
                                 exit_triggered = True
                                 exit_reason = "RSI_TARGET"

                if exit_triggered:
                    # Execute Exit
                    # Calc Cost
                    # quantity = int(current_equity / entry_price) # simplified partial compounding
                    # PnL = (exit_price - entry_price) * quantity

                    # Using percentage return for equity curve to be scale invariant
                    raw_ret = (exit_price - entry_price) / entry_price

                    # Apply Costs (approx bps)
                    # 5 bps slippage per side = 10 bps total
                    # Brokerage etc.
                    # Let's use 0.1% round trip approx for simplicity or use cost model.
                    cost_bps = 10 + 10 # 20 bps total slippage + txn
                    cost_pct = cost_bps / 10000.0

                    net_ret = raw_ret - cost_pct

                    current_equity *= (1 + net_ret)

                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": dt,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return": net_ret,
                        "reason": exit_reason
                    })

                    position = 0
                    entry_price = 0.0

            # Check Entry (if not in position)
            # We check signal from PREVIOUS day to enter TODAY at OPEN
            if position == 0:
                if entry_signal.iloc[i-1]:
                    position = 1
                    entry_price = opens[i]
                    entry_idx = i
                    # Cost of entry is accounted for at exit or we can deduct now.
                    # We deducted round trip at exit above.

            equity_curve.append(current_equity)

        equity_series = pd.Series(equity_curve, index=df.index[:len(equity_curve)])

        return {
            "trades": pd.DataFrame(trades),
            "equity_curve": equity_series,
            "final_equity": current_equity,
            "rule_summary": summarize_rules(strategy_config),
            "is_open": position == 1
        }
