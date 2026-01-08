"""
Backtest Engine.
Runs daily backtest for a strategy candidate.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.factory.generator import StrategyInterpreter
from packages.strategy_foundry.adapters.core_costs import DEFAULT_COST_MODEL, CostModel
from packages.strategy_foundry.adapters import core_indicators as ind

class BacktestEngine:
    def __init__(self, cost_model: CostModel = DEFAULT_COST_MODEL):
        self.cost_model = cost_model

    def run(self, df: pd.DataFrame, candidate: StrategyCandidate, initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        Run backtest.
        Returns metrics and curves.
        """
        interpreter = StrategyInterpreter(candidate)

        # 1. Generate Raw Signals
        raw_signals = interpreter.generate_positions(df)
        risk_params = interpreter.get_risk_params()

        # 2. Loop for execution (needed for path-dependent stops)
        # We'll use a fast loop (numba not allowed, but simple python loop over array is okay for daily data)
        # Daily data ~ 2500 rows for 10 years. Fast enough.

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        dates = df.index

        # Pre-calculate ATR for stops if needed
        atr_series = None
        if risk_params.get("type") == "ATR_STOP":
            p = risk_params["params"]
            atr_series = ind.atr(df, period=p["period"]).values

        position = 0 # Current position: 1, -1, 0
        entry_price = 0.0
        equity = initial_capital
        cash = initial_capital

        trades = []
        equity_curve = []

        current_stop = None

        for i in range(1, len(df)):
            # Market Data
            date = dates[i]
            open_p = df["open"].values[i] # Execution at Open of next bar
            close_p = closes[i]
            high_p = highs[i]
            low_p = lows[i]

            # Previous Bar Signal (generated at close of i-1)
            signal = raw_signals.iloc[i-1]

            # Check Exits first (Stops)
            exit_price = None
            exit_reason = None

            if position != 0:
                # Check Stop Loss
                if position == 1:
                    if low_p < current_stop:
                        exit_price = min(open_p, current_stop) # Gap handling: exit at open if gap down below stop
                        # Ideally, if open < stop, we exit at open. If open > stop, we exit at stop.
                        # Wait, if Low < Stop, we hit it.
                        # If Open < Stop, we gapped over it -> execute at Open.
                        # If Open > Stop, we executed at Stop.
                        if open_p < current_stop:
                            exit_price = open_p
                        else:
                            exit_price = current_stop
                        exit_reason = "STOP"
                elif position == -1:
                    if high_p > current_stop:
                        if open_p > current_stop:
                            exit_price = open_p
                        else:
                            exit_price = current_stop
                        exit_reason = "STOP"

                # Check Signal Reversal
                if exit_price is None and signal != 0 and signal != position:
                    exit_price = open_p
                    exit_reason = "SIGNAL"

                # Execute Exit
                if exit_price is not None:
                    # Calculate PnL
                    qty = abs(position) # Assume size 1 unit or full capital?
                    # Let's use fixed capital allocation for simplicity or 1 unit.
                    # Requirement: "equity curve series".
                    # Let's simulate fully invested 100% equity for simplicity to get CAGR/Drawdown.
                    # Or simpler: calculate % returns.

                    # Implementation: Track value of holdings.
                    # On Entry: shares = cash / open_p
                    # On Exit: cash = shares * exit_price - costs

                    # We need to track `shares`.
                    pass # Handled below in integrated logic

            # Integrated Logic
            # 1. Update Portfolio Value (Mark to Market)
            # If we hold position, value = shares * close_p
            # We record equity at End of Day.

            # Logic:
            # - Check Stop Hit during day i (using high/low)
            # - Check Signal from i-1 (executed at Open of i)

            # Current State
            prev_equity = equity_curve[-1] if equity_curve else initial_capital

            # Check Stop (Intraday)
            stop_hit = False
            if position != 0 and current_stop is not None:
                if position == 1 and low_p <= current_stop:
                    # Exited
                    exit_p = open_p if open_p < current_stop else current_stop
                    cost = self.cost_model.estimate_cost(exit_p, 1, "SELL") # per unit cost?
                    # We need to track 'holding_qty'.

                    # Let's use % return logic for simplicity and speed, then scale to equity.
                    # Trade Return = (Exit - Entry) / Entry * Side
                    # Cost deduct.

                    pct_change = (exit_p - entry_price) / entry_price
                    # Deduct costs (approximate as bps of price)
                    # cost_bps = slippage + brokerage + tax
                    # We'll use the cost model to get a value, convert to %

                    # Re-implement using Cash/Qty
                    # Sell
                    proceeds = holding_qty * exit_p
                    c = self.cost_model.estimate_cost(exit_p, holding_qty, "SELL")
                    cash = proceeds - c
                    equity = cash

                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": date,
                        "entry_price": entry_price,
                        "exit_price": exit_p,
                        "side": "LONG",
                        "pnl": equity - capital_at_entry,
                        "return": (equity - capital_at_entry)/capital_at_entry,
                        "reason": "STOP"
                    })

                    position = 0
                    holding_qty = 0
                    stop_hit = True

                elif position == -1 and high_p >= current_stop:
                     # Short Stop
                     # Shorting: Borrow shares, sell, buy back.
                     # Entry: Cash + Short Proceeds. Liability = Qty * Price.
                     # Equity = Cash - Liability.

                     # Simplified: Inverse ETF logic.
                     # Exit
                     exit_p = open_p if open_p > current_stop else current_stop

                     # Buy to cover
                     cost_to_buy = holding_qty * exit_p
                     c = self.cost_model.estimate_cost(exit_p, holding_qty, "BUY")
                     cash = cash - cost_to_buy - c # Cash was holding the short proceeds + initial

                     equity = cash

                     trades.append({
                        "entry_date": entry_date,
                        "exit_date": date,
                        "entry_price": entry_price,
                        "exit_price": exit_p,
                        "side": "SHORT",
                        "pnl": equity - capital_at_entry,
                        "return": (equity - capital_at_entry)/capital_at_entry,
                        "reason": "STOP"
                     })

                     position = 0
                     holding_qty = 0
                     stop_hit = True

            # Process Entry/Reversal if no stop hit today
            # Signal from i-1 means we trade at Open of i.
            # Only trade if position matches signal?
            # If position is 0 and signal != 0 -> Entry
            # If position != 0 and signal != position -> Reversal (Exit + Entry)
            # If position != 0 and signal == position -> Hold

            if not stop_hit:
                if signal != 0 and signal != position:
                    # Exit existing
                    if position != 0:
                        # Close current
                        if position == 1:
                            proceeds = holding_qty * open_p
                            c = self.cost_model.estimate_cost(open_p, holding_qty, "SELL")
                            cash = proceeds - c
                            side = "LONG"
                        else:
                            cost_to_buy = holding_qty * open_p
                            c = self.cost_model.estimate_cost(open_p, holding_qty, "BUY")
                            cash = cash - cost_to_buy - c
                            side = "SHORT"

                        equity = cash
                        trades.append({
                            "entry_date": entry_date,
                            "exit_date": date,
                            "entry_price": entry_price,
                            "exit_price": open_p,
                            "side": side,
                            "pnl": equity - capital_at_entry,
                            "return": (equity - capital_at_entry)/capital_at_entry,
                            "reason": "SIGNAL"
                        })
                        position = 0
                        holding_qty = 0

                    # Enter new
                    if signal == 1: # Long
                        # Buy max shares
                        # Cost estimate?
                        # cash = qty * open_p + cost(qty)
                        # approx qty = cash / open_p
                        qty = int(cash / open_p)
                        if qty > 0:
                            c = self.cost_model.estimate_cost(open_p, qty, "BUY")
                            cost_basis = qty * open_p + c
                            if cost_basis <= cash:
                                cash -= cost_basis # For long, cash becomes 0 (all in assets)
                                # Wait, cash is just cash balance.
                                # Equity = Cash + Asset Value.
                                # We spent cash to buy assets.
                                # Asset Value = qty * current_price.
                                # Remaining Cash = Cash - Cost Basis.
                                holding_qty = qty
                                position = 1
                                entry_price = open_p
                                entry_date = date
                                capital_at_entry = equity # snapshot

                                # Set Stop
                                if risk_params.get("type") == "ATR_STOP":
                                    mult = risk_params["params"]["multiplier"]
                                    # Use ATR from i-1 (known at open)
                                    val_atr = atr_series[i-1] if not np.isnan(atr_series[i-1]) else 0
                                    current_stop = open_p - (val_atr * mult)
                                elif risk_params.get("type") == "TRAILING_STOP":
                                    pct = risk_params["params"]["pct"]
                                    current_stop = open_p * (1 - pct/100)
                                else:
                                    current_stop = 0 # Safety

                    elif signal == -1: # Short
                        # Assume we can short with full capital (1x leverage)
                        # Margin required = Value.
                        # We keep cash. We add proceeds? No, retail short usually requires margin.
                        # Simple model:
                        # We 'sell' qty. We have cash = initial + sell_proceeds.
                        # Liability = qty * price.
                        # Equity = Cash - Liability.

                        qty = int(cash / open_p)
                        if qty > 0:
                            c = self.cost_model.estimate_cost(open_p, qty, "SELL")
                            # Short entry cost
                            cash = cash - c # Pay cost
                            # We are short `qty`.
                            # Cash balance remains `cash` (plus notionally the short proceeds, but usually margin locks it).
                            # Let's track:
                            # Cash Balance (Virtual) = Old Cash + (Qty * Open P)
                            # To Close: Pay (Qty * Close P)
                            # Equity = Virtual Cash - (Qty * Close P)

                            short_proceeds = qty * open_p
                            cash = cash + short_proceeds

                            holding_qty = qty
                            position = -1
                            entry_price = open_p
                            entry_date = date
                            capital_at_entry = equity

                            # Set Stop
                            if risk_params.get("type") == "ATR_STOP":
                                mult = risk_params["params"]["multiplier"]
                                val_atr = atr_series[i-1] if not np.isnan(atr_series[i-1]) else 0
                                current_stop = open_p + (val_atr * mult)
                            elif risk_params.get("type") == "TRAILING_STOP":
                                pct = risk_params["params"]["pct"]
                                current_stop = open_p * (1 + pct/100)
                            else:
                                current_stop = float('inf')

            # Update Trailing Stop if needed (End of Day)
            if position == 1 and risk_params.get("type") == "TRAILING_STOP":
                pct = risk_params["params"]["pct"]
                new_stop = close_p * (1 - pct/100)
                if new_stop > current_stop:
                    current_stop = new_stop
            elif position == -1 and risk_params.get("type") == "TRAILING_STOP":
                pct = risk_params["params"]["pct"]
                new_stop = close_p * (1 + pct/100)
                if new_stop < current_stop:
                    current_stop = new_stop

            # Mark to Market Equity
            if position == 1:
                mv = holding_qty * close_p
                equity = cash + mv # Cash is remaining cash after buy
            elif position == -1:
                liability = holding_qty * close_p
                equity = cash - liability
            else:
                equity = cash

            equity_curve.append({"date": date, "equity": equity})

        return {
            "trades": pd.DataFrame(trades),
            "equity_curve": pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(),
            "final_equity": equity
        }
