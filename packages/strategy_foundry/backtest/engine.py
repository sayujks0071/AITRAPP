# StrategyFoundry Implementation
import pandas as pd
import numpy as np
import structlog
from typing import List, Dict, Tuple
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.adapters.core_costs import CostAdapter

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, costs: Dict = None):
        self.initial_capital = initial_capital
        self.costs = costs or {"all_in_cost_bps_per_side": 3.0, "slippage_bps_per_side": 2.0, "spread_guard_bps": 1.0}
        self.market_guard = MarketHoursAdapter()
        self.cost_adapter = CostAdapter()

    def run(self, strategy: Strategy, data: pd.DataFrame) -> Tuple[pd.Series, List[Dict]]:
        """
        Run backtest.
        Returns: (Equity Curve, Trades List)
        """
        if data.empty:
            return pd.Series(), []

        # 1. Calculate Signals (Vectorized)
        entries, exits = strategy.calculate_signals(data)
        risk_params = strategy.get_risk_params()

        # 2. Loop
        capital = self.initial_capital
        equity_curve = []
        trades = []

        position = 0 # 0, 1 (Long), -1 (Short)
        entry_price = 0.0
        entry_time = None
        entry_bar_idx = 0

        # Precompute arrays for speed
        opens = data["open"].values
        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values
        times = data.index

        entry_sigs = entries.values
        exit_sigs = exits.values

        n = len(data)

        # Tracking High/Low for Trailing Stop
        highest_since_entry = 0.0
        lowest_since_entry = 0.0

        for i in range(n - 1): # Stop at n-1 because we execute on i+1
            timestamp = times[i]

            # Record Equity (Mark to Market)
            current_val = capital
            if position != 0:
                # Unrealized PnL based on Close
                # Simplified: assumes we hold 'capital' worth of stock?
                # Or fixed quantity?
                # "Position Sizing: Default 1x notional"
                # Means if capital is 100k, we buy 100k worth.
                # So quantity = capital / entry_price (at entry).
                # But capital changes. Let's use Fixed Fraction of Current Equity.

                # Wait, we need to track Quantity.
                pass

            # Since we only update capital on close, let's just track trade PnL for simplicity in this loop
            # and reconstruct equity curve later or update daily.
            # But for trailing stop we need intra-bar logic? No, we use bar OHLC.

            # Execution Logic:
            # Decisions made at Close of bar i, executed at Open of bar i+1.

            # 1. Check Exits for EXISTING position
            if position != 0:
                exit_reason = None

                # Market Close Exit (Hard)
                # Check if bar i is the last bar of session or close to it
                # We use i+1 time for execution, so if i+1 is next day, we MUST have exited at i close?
                # Actually, "All positions flat by 15:25".
                # If timestamp is >= 15:25, we should have exited.
                if self.market_guard.is_session_closing(timestamp):
                    exit_reason = "session_close"

                # Signal Exit
                elif exit_sigs[i]:
                    exit_reason = "signal_exit"

                # Time Stop
                elif "time_stop_bars" in risk_params:
                    bars_held = i - entry_bar_idx
                    if bars_held >= risk_params["time_stop_bars"]:
                        exit_reason = "time_stop"

                # Trailing Stop (ATR) - Requires ATR calculation which might be complex inside loop
                # For now assume fixed % trail or simplifed.
                # If Strategy returned a stop level, we could use it.
                # Let's skip complex trailing stop inside this loop for MVP unless precomputed.

                # Update High/Low since entry
                if position == 1:
                    if highs[i] > highest_since_entry:
                        highest_since_entry = highs[i]
                elif position == -1:
                    if lows[i] < lowest_since_entry or lowest_since_entry == 0.0:
                        lowest_since_entry = lows[i]

                # Percentage Trailing Stop
                if not exit_reason and "trailing_stop_pct" in risk_params:
                    pct = risk_params["trailing_stop_pct"]
                    if position == 1:
                        stop_price = highest_since_entry * (1.0 - pct)
                        if lows[i] < stop_price:
                            exit_reason = "trailing_stop"
                    elif position == -1:
                        stop_price = lowest_since_entry * (1.0 + pct)
                        if highs[i] > stop_price:
                            exit_reason = "trailing_stop"

                if exit_reason:
                    # Execute Exit at Open of i+1
                    exit_price = opens[i+1]
                    # Apply slippage
                    slip = exit_price * (self.costs["slippage_bps_per_side"] / 10000.0)
                    if position == 1:
                        exec_price = exit_price - slip
                    else:
                        exec_price = exit_price + slip

                    # PnL
                    # Qty determined at entry
                    qty = (self.initial_capital) / entry_price # Fixed size based on initial for simplicity or compounding?
                    # Let's use Compounding: qty = capital / entry_price
                    # But we need to track capital properly.

                    # Correction: Loop variable `capital` tracks current equity.
                    qty = capital / entry_price

                    gross_pnl = (exec_price - entry_price) * qty * position

                    # Costs
                    bps_cost = self.costs["all_in_cost_bps_per_side"] / 10000.0
                    cost = (entry_price * qty * bps_cost) + (exec_price * qty * bps_cost)
                    # Spread guard
                    cost += (entry_price * qty * (self.costs["spread_guard_bps"] / 10000.0))

                    net_pnl = gross_pnl - cost
                    capital += net_pnl

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": times[i+1],
                        "entry_price": entry_price,
                        "exit_price": exec_price,
                        "pnl": net_pnl,
                        "return_pct": (net_pnl / (entry_price * qty)) * 100,
                        "reason": exit_reason
                    })

                    position = 0
                    continue # Position closed, can we enter same bar? Usually no.

            # 2. Check Entries (if flat)
            if position == 0:
                # Check Market Hours for Entry
                if self.market_guard.is_market_open(timestamp) and not self.market_guard.is_session_closing(timestamp):
                    if entry_sigs[i] != 0:
                        direction = entry_sigs[i] # 1 or -1
                        # Execute Entry at Open i+1
                        entry_price_raw = opens[i+1]

                        # Slip
                        slip = entry_price_raw * (self.costs["slippage_bps_per_side"] / 10000.0)
                        if direction == 1:
                            entry_price = entry_price_raw + slip
                        else:
                            entry_price = entry_price_raw - slip

                        position = direction
                        entry_time = times[i+1]
                        entry_bar_idx = i+1
                        highest_since_entry = entry_price
                        lowest_since_entry = entry_price

            # Record Equity Curve (at Close of i)
            # Use 'capital' (cash) + unrealized PnL
            if position != 0:
                # Mark to Close[i]
                curr_price = closes[i]
                qty = capital / entry_price # This is approximation, technically capital was cash before entry
                # Let's be more precise:
                # Cash = 0 (fully invested). Asset Value = qty * curr_price.
                # Initial Cost = qty * entry_price.
                # Unrealized = (curr_price - entry_price) * qty * position
                # Equity = Capital (at entry) + Unrealized
                # But we need to deduct entry costs?
                # Let's keep `capital` as "Account Value".

                unrealized = (curr_price - entry_price) * (capital / entry_price) * position
                equity_curve.append(capital + unrealized)
            else:
                equity_curve.append(capital)

        # Append last
        equity_curve.append(capital)

        # Convert to Series
        # equity_curve length is n (or n-1?), loop went n-1.
        # We appended n times.
        # Ensure index match.
        eq_series = pd.Series(equity_curve, index=times[:len(equity_curve)])

        return eq_series, trades
