"""Backtest engine for intraday strategies"""
import pandas as pd
import numpy as np
import structlog
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time

from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyBlock
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 cost_bps: float = 5.0, slippage_bps: float = 5.0):
        self.data = data
        self.initial_capital = initial_capital
        # Total cost per side in basis points
        self.total_cost_bps = cost_bps + slippage_bps
        self.indicators_adapter = IndicatorsAdapter()

    def run(self, candidate: StrategyCandidate) -> Dict:
        """
        Run backtest for a single candidate.
        Returns metrics dict and equity curve DataFrame.
        """
        # 1. Prepare Features (Indicators)
        df = self.data.copy()

        # Calculate indicators required by blocks
        # This is a simplified simulation. In a real highly optimized engine,
        # we'd precompute common indicators. Here we compute on fly.
        self._compute_indicators(df, candidate)

        # 2. Generate Signals
        entries = self._evaluate_entry(df, candidate.entry_block, candidate.filter_blocks)

        # 3. Sim Loop
        # Vectorized is hard with complex exits (trailing, time stop).
        # We will use a fast iterative loop with Numba or just optimized Python.
        # Given the scope, optimized Python loop.

        trades = []
        equity = [self.initial_capital]
        position = 0 # 1 (Long), 0 (Flat), -1 (Short - if enabled)
        entry_price = 0.0
        entry_time = None
        stop_loss = 0.0
        take_profit = 0.0
        bars_held = 0

        # Pre-calc columns for speed
        open_arr = df['open'].values
        high_arr = df['high'].values
        low_arr = df['low'].values
        close_arr = df['close'].values
        time_arr = df.index.time
        date_arr = df.index.date

        entry_signal_arr = entries.values

        # Extract exit params
        atr_stop_mult = None
        atr_stop_period = None
        profit_target_mult = None
        time_stop_bars = None

        for block in candidate.exit_blocks:
            if block.name == "ATRStop":
                atr_stop_mult = block.params["multiplier"]
                atr_stop_period = block.params["period"]
            elif block.name == "ProfitTarget":
                profit_target_mult = block.params["atr_multiplier"]
            elif block.name == "TimeStop":
                time_stop_bars = block.params["max_bars"]

        atr_arr = None
        if atr_stop_mult or profit_target_mult:
            # Ensure ATR is calculated
            period = atr_stop_period if atr_stop_period else 14
            col = f"atr_{period}"
            if col in df.columns:
                atr_arr = df[col].values
            else:
                # Fallback if not computed (should happen in _compute_indicators)
                atr_arr = np.zeros(len(df))

        capital = self.initial_capital

        # Hard close time: 15:25
        hard_close_time = time(15, 25)

        n_bars = len(df)

        for i in range(1, n_bars):
            # Current Bar
            ts = df.index[i]
            curr_time = time_arr[i]
            curr_date = date_arr[i]
            prev_date = date_arr[i-1]

            # Open Price of current bar is execution price for signals from previous close
            # But wait, our 'entries' array is aligned to bar CLOSE.
            # So if entries[i-1] is True, we enter at open_arr[i].

            exec_price = open_arr[i]

            # --- Check Exits first ---
            if position != 0:
                bars_held += 1
                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""

                # 1. EOD Exit (Must close if time >= 15:25)
                if curr_time >= hard_close_time:
                    exit_triggered = True
                    exit_price = open_arr[i] # Close at open of this bar if it's late
                    exit_reason = "EOD"

                # 2. Stop Loss / Take Profit (Hit within the bar)
                if not exit_triggered:
                    # Check Low for Long Stop
                    if position > 0:
                        if low_arr[i] <= stop_loss:
                            exit_triggered = True
                            exit_price = stop_loss # Assumption: filled at stop
                            # Apply slippage later, but for simulation, hitting stop is bad
                            # To be conservative, use MIN(stop_loss, open_arr[i]) if gap down?
                            if open_arr[i] < stop_loss:
                                exit_price = open_arr[i]
                            exit_reason = "SL"
                        elif take_profit > 0 and high_arr[i] >= take_profit:
                            exit_triggered = True
                            exit_price = take_profit
                            if open_arr[i] > take_profit:
                                exit_price = open_arr[i]
                            exit_reason = "TP"

                # 3. Time Stop
                if not exit_triggered and time_stop_bars and bars_held >= time_stop_bars:
                    exit_triggered = True
                    exit_price = open_arr[i] # Close at open of current bar
                    exit_reason = "Time"

                if exit_triggered:
                    # Execute Exit
                    cost = exit_price * (self.total_cost_bps / 10000.0)
                    pnl = (exit_price - entry_price) * position - cost - (entry_price * self.total_cost_bps / 10000.0)

                    capital += pnl * (self.initial_capital / entry_price) # Fixed fractional simplified: buying 1 unit normalized?
                    # Let's fix position sizing: 1 unit for simplicity in raw pnl, then scale.
                    # Or simpler: compute % return.

                    ret = (exit_price - entry_price) / entry_price
                    # Adjust for costs
                    ret -= (self.total_cost_bps * 2) / 10000.0

                    # Update Capital
                    # Assume 100% equity allocated per trade
                    capital = capital * (1 + ret)

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": ret,
                        "reason": exit_reason,
                        "bars": bars_held
                    })

                    position = 0
                    bars_held = 0

            # --- Check Entries ---
            # If flat and signal from PREVIOUS bar close
            if position == 0:
                # Signal at i-1
                if entry_signal_arr[i-1]:
                    # Check if market is about to close, don't enter
                    if curr_time < time(15, 0): # Don't enter after 15:00
                        position = 1 # Long only for now
                        entry_price = exec_price
                        entry_time = ts
                        bars_held = 0

                        # Set SL/TP
                        current_atr = atr_arr[i-1] if atr_arr is not None else 0

                        if atr_stop_mult and current_atr > 0:
                            stop_loss = entry_price - (current_atr * atr_stop_mult)
                        else:
                            stop_loss = entry_price * 0.99 # Default 1% safety

                        if profit_target_mult and current_atr > 0:
                            take_profit = entry_price + (current_atr * profit_target_mult)
                        else:
                            take_profit = 0.0 # No target

            equity.append(capital)

        return {
            "trades": pd.DataFrame(trades),
            "equity": pd.Series(equity, index=df.index),
            "final_capital": capital,
            "final_position": position
        }

    def _compute_indicators(self, df: pd.DataFrame, candidate: StrategyCandidate):
        # Scan blocks and compute needed indicators
        # Add to df columns
        self.indicators_adapter.compute_for_blocks(df, candidate.entry_block)
        for b in candidate.exit_blocks:
            self.indicators_adapter.compute_for_blocks(df, b)
        for b in candidate.filter_blocks:
            self.indicators_adapter.compute_for_blocks(df, b)

    def _evaluate_entry(self, df: pd.DataFrame, entry: StrategyBlock, filters: List[StrategyBlock]) -> pd.Series:
        # Evaluate Entry condition
        entry_sig = self.indicators_adapter.evaluate_condition(df, entry)

        # Apply filters
        for f in filters:
            f_sig = self.indicators_adapter.evaluate_condition(df, f)
            entry_sig = entry_sig & f_sig

        return entry_sig

