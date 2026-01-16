"""Vectorized Backtest Engine"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from ..factory.generator import StrategyCandidate
from ..adapters.core_indicators import VectorIndicatorCalculator
from .costs import CostModel
from .metrics import calculate_metrics

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, allow_short: bool = False):
        self.initial_capital = initial_capital
        self.allow_short = allow_short
        self.cost_model = CostModel()
        self.calc = VectorIndicatorCalculator()

    def run(self, df: pd.DataFrame, strategy: StrategyCandidate) -> Dict[str, Any]:
        """
        Run backtest for a single strategy on a dataframe.
        """
        # 1. Pre-calculate indicators needed (optimisation: calc all once per df outside?)
        # For now, we assume strategy calculates what it needs or we provide all.
        # Let's provide a dict of ALL common indicators to avoid re-calc per rule
        # In a real heavy loop, we'd cache this per DF.

        indicators = self._calc_indicators(df)

        # 2. Generate Signals
        raw_signals = strategy.generate_positions(df, indicators)

        # 3. Simulate Execution
        trades, equity = self._simulate(df, raw_signals, strategy.stop_loss)

        # 4. Metrics
        metrics = calculate_metrics(equity, trades)

        return {
            "metrics": metrics,
            "trades": trades,
            "equity": equity
        }

    def _calc_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        # Calculate common pool
        d = {}
        # EMAs
        d['ema_9'] = self.calc.ema(df['close'], 9)
        d['ema_21'] = self.calc.ema(df['close'], 21)
        d['ema_34'] = self.calc.ema(df['close'], 34)
        d['ema_55'] = self.calc.ema(df['close'], 55)
        d['ema_89'] = self.calc.ema(df['close'], 89)
        d['ema_144'] = self.calc.ema(df['close'], 144)
        d['ema_200'] = self.calc.ema(df['close'], 200)

        # RSI
        d['rsi_7'] = self.calc.rsi(df, 7)
        d['rsi_14'] = self.calc.rsi(df, 14)
        d['rsi_21'] = self.calc.rsi(df, 21)

        # Supertrend
        for p in [7, 10, 14]:
            for m in [1.5, 2.0, 3.0]:
                st, direction = self.calc.supertrend(df, p, m)
                d[f"st_val_{p}_{m}"] = st
                d[f"st_dir_{p}_{m}"] = direction

        # ATR (for stops)
        d['atr_14'] = self.calc.atr(df, 14)

        return d

    def _simulate(self, df: pd.DataFrame, signals: pd.Series, stop_rule) -> tuple:
        """
        Simulate trade execution with next-open logic and ATR stops.
        """
        # Signals: 1 (Long), -1 (Short), 0 (Flat)
        # We execute at OPEN of i+1 based on Signal at i

        # Force signals to 0 if short not allowed
        if not self.allow_short:
             signals = signals.replace(-1, 0)

        trades = []
        equity_curve = []
        cash = self.initial_capital
        position = 0 # 0, 1, -1
        entry_price = 0.0
        entry_idx = None
        quantity = 0

        # For ATR Stop
        atr_series = self.calc.atr(df, stop_rule.atr_period)
        stop_mul = stop_rule.multiplier

        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        dates = df.index

        curr_equity = cash

        for i in range(len(df) - 1):
            # Record Equity (Mark to Market)
            if position != 0:
                mtm_price = closes[i]
                # Simplified MTM (ignoring costs for equity curve smoothness)
                val = quantity * mtm_price
                if position == 1:
                    curr_equity = cash + val
                else:
                    # Short: Cash has entry proceeds. Liability is buyback cost.
                    # This logic is tricky. Let's simplify:
                    # Cash tracks realized. We add unrealized PnL.
                    # PnL = (Entry - Current) * Qty
                    pnl = (entry_price - mtm_price) * quantity
                    # To get total equity, we need Base + PnL.
                    # But we updated cash on entry?
                    # Let's stick to: Cash = Realized Cash.
                    # Equity = Cash + Unrealized PnL.
                    # Note: cost model returns net cash change.

                    # Wait, let's use a simpler accounting:
                    # Cash is cash. Position value is value.
                    # For Long: Eq = Cash + (Price * Qty)
                    # For Short: Eq = Cash + (EntryPrice * Qty) - (Price * Qty) ?
                    #   Actually on short entry we sold, so we got cash.
                    #   So Cash includes the short proceeds.
                    #   Equity = Cash - (Price * Qty) (Cost to cover)
                    curr_equity = cash - (val)

            equity_curve.append(curr_equity)

            # Logic for NEXT bar execution
            # Check stops first (intra-bar on current bar i)
            # Actually, if we are in pos, we check if High/Low hit stop today

            if position != 0:
                # Check Stop Loss on Bar i
                # Stop price determined at entry
                hit_stop = False
                exit_price = 0.0

                if position == 1:
                    stop_price = entry_price - (atr_at_entry * stop_mul)
                    if lows[i] < stop_price:
                        hit_stop = True
                        exit_price = stop_price # Assume fill at stop (slippage handled in cost?)
                        # In reality, gap down? Use min(Open, Stop)?
                        # Conservative: Use Stop Price (perfect execution) or Low (worst case)?
                        # Let's use Stop Price minus slippage later.
                        # Ideally: If Open < Stop, we exit at Open. Else at Stop.
                        if opens[i] < stop_price: exit_price = opens[i]

                elif position == -1:
                    stop_price = entry_price + (atr_at_entry * stop_mul)
                    if highs[i] > stop_price:
                        hit_stop = True
                        exit_price = stop_price
                        if opens[i] > stop_price: exit_price = opens[i]

                if hit_stop:
                    # Execute Exit
                    cost = self.cost_model.apply(exit_price, quantity, -position) # Sell if long (1->-1), Buy if short (-1->1)
                    # Cost model returns net cash change
                    cash += cost

                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": dates[i],
                        "pnl": (exit_price - entry_price) * quantity * position, # Approx raw pnl
                        # Accurate PnL is diff in cash accounting, but let's store approx
                    })

                    position = 0
                    quantity = 0
                    continue # Position closed, wait for next signal

            # Signal Generation (at end of bar i, for open of i+1)
            sig = signals.iloc[i]

            # Execution at Open of i+1
            next_open = opens[i+1]

            if sig != 0 and sig != position:
                # Reverse or Open

                # 1. Close existing if any
                if position != 0:
                    cost = self.cost_model.apply(next_open, quantity, -position)
                    cash += cost
                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": dates[i+1],
                        "pnl": 0 # metrics calc from equity curve mostly? No trades table needs pnl.
                        # We need to track realized pnl properly.
                    })
                    # Recalculate PnL properly:
                    # We rely on cash delta for total equity, but for trade stats we need entry/exit prices.
                    trades[-1]['pnl'] = (next_open - entry_price) * quantity * position

                    position = 0
                    quantity = 0

                # 2. Open new
                # Calc Quantity: Risk based? Or Fixed Capital?
                # Simple: Allocate 100% equity
                qty = int(curr_equity / next_open)
                if qty > 0:
                    cost = self.cost_model.apply(next_open, qty, sig)
                    cash += cost # Deduct cost (negative for buy)

                    position = sig
                    quantity = qty
                    entry_price = next_open
                    entry_idx = i+1
                    atr_at_entry = atr_series.iloc[i] # Use ATR from signal bar

        # Append final equity
        equity_curve.append(curr_equity)

        # Format results
        equity_series = pd.Series(equity_curve, index=dates[:len(equity_curve)])
        trades_df = pd.DataFrame(trades)
        if trades_df.empty:
            trades_df = pd.DataFrame(columns=['entry_date', 'exit_date', 'pnl'])

        return trades_df, equity_series

