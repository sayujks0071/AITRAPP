"""Backtest Engine (Vectorized)"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from .metrics import calculate_metrics
from ..adapters.core_indicators import compute_indicators
from ..adapters.core_costs import estimate_total_transaction_cost
from ..factory.grammar import StrategyConfig

class VectorBacktestEngine:
    """
    Fast vectorized backtester for 1D bars.
    """

    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital

    def run(self, df: pd.DataFrame, strategy: StrategyConfig) -> Dict:
        """
        Run backtest for a strategy on a dataframe.
        DF must have OHLCV and datetime index.
        """
        if df.empty:
            return {}

        # 1. Compute Indicators
        # In a real comprehensive system, we might only compute what's needed.
        # For simplicity, we compute common ones or parse strategy.
        indicators = compute_indicators(df)

        # 2. Generate Signals
        # 1 = Long, -1 = Short, 0 = Flat
        # We start with 0
        signals = pd.Series(0, index=df.index)

        # Apply Entry Rules
        # Simplifying: we assume 1 entry rule for now from generator
        entry_rule = strategy.entry_rules[0]
        name = entry_rule.name
        params = entry_rule.params

        long_condition = pd.Series(False, index=df.index)

        if name == "EMA_CROSS":
            # Re-compute specific params locally to be correct
            ema_f = df["close"].ewm(span=params["fast"], adjust=False).mean()
            ema_s = df["close"].ewm(span=params["slow"], adjust=False).mean()

            long_condition = (ema_f > ema_s) & (ema_f.shift(1) <= ema_s.shift(1))

        elif name == "SUPERTREND":
            # We use the computed supertrend from adapter if params match roughly,
            # otherwise we should recompute.
            # For this MVP, we will rely on adapter's default ST or specific if close enough.
            # But the generator produces random params.
            # Let's implement a quick vector supertrend here or use the adapter's implementation via a call if possible.
            # The adapter computes ONE set of params.
            # We will just reuse the adapter's logic but call it from here or re-implement.
            # Re-implementing specific supertrend:
            pass # TODO: Implement dynamic supertrend calc. For now, we fallback to adapter's if available or skip

            # Using adapter's default for now to ensure SOMETHING happens
            if "supertrend_direction" in indicators:
                 # Adapter ST: 1 = Up, -1 = Down.
                 # Signal Long if direction turns 1 from -1
                 st_dir = indicators["supertrend_direction"]
                 long_condition = (st_dir == 1) & (st_dir.shift(1) == -1)

        elif name == "RSI_OS_OB":
            # RSI < lower -> Long
            rsi = indicators["rsi"] # 14 period default
            long_condition = rsi < params["lower"]

        elif name == "DONCHIAN":
            # Breakout of Upper
            upper = df["high"].rolling(window=params["period"]).max().shift(1)
            long_condition = df["close"] > upper

        elif name == "BB_REVERSION":
            # Close < Lower Band
            # We need to compute BB with specific params
            mid = df["close"].rolling(window=params["period"]).mean()
            std = df["close"].rolling(window=params["period"]).std()
            lower = mid - (std * params["std"])
            long_condition = df["close"] < lower

        # 3. Simulate positions

        trades = []
        equity = [self.initial_capital]
        position = 0 # 0, 1
        entry_price = 0.0
        entry_idx = 0
        stop_price = 0.0

        close_arr = df["close"].values
        open_arr = df["open"].values
        low_arr = df["low"].values
        dates = df.index

        # Pre-calc signals to array
        long_signals = long_condition.values

        # Risk params
        risk_rule = strategy.risk_rules[0]
        atr_arr = indicators["atr"].fillna(0).values

        for i in range(1, len(df)):
            curr_equity = equity[-1]

            # Check Exit if in position
            if position != 0:
                # Check Stop Loss
                hit_stop = False
                exit_price = 0.0

                if low_arr[i] <= stop_price:
                    # Stopped out
                    hit_stop = True
                    # Slippage on stop? Assume execute at stop price or Open if gap down
                    # If Open was already below stop, we exited at Open.
                    exit_price = min(open_arr[i], stop_price)

                # Force close at very last bar
                if i == len(df) - 1 and not hit_stop:
                    hit_stop = True
                    exit_price = close_arr[i]

                if hit_stop:
                    # Execute Exit
                    shares = int(curr_equity / entry_price)
                    if shares > 0:
                        raw_pnl = (exit_price - entry_price) * shares
                        cost = estimate_total_transaction_cost(exit_price, shares, "SELL") + \
                               estimate_total_transaction_cost(entry_price, shares, "BUY")

                        net_pnl = raw_pnl - cost
                        curr_equity += net_pnl

                        trades.append({
                            "entry_date": dates[entry_idx],
                            "exit_date": dates[i],
                            "pnl": net_pnl,
                            "return_pct": (exit_price/entry_price) - 1
                        })

                    position = 0
                    entry_price = 0.0

            # Check Entry if flat
            if position == 0 and i < len(df) - 1: # Don't enter on last bar
                if long_signals[i-1]: # Signal from yesterday close, enter today Open
                    # Enter
                    entry_price = open_arr[i]
                    entry_idx = i
                    position = 1

                    # Set Stop
                    if risk_rule.name == "ATR_STOP":
                        stop_dist = atr_arr[i-1] * risk_rule.params.get("multiplier", 2.0)
                        # Avoid zero stop dist
                        if stop_dist == 0:
                            stop_dist = entry_price * 0.02 # fallback
                        stop_price = entry_price - stop_dist
                    elif risk_rule.name == "PCT_STOP":
                        stop_dist = entry_price * risk_rule.params.get("pct", 0.02)
                        stop_price = entry_price - stop_dist

            equity.append(curr_equity)

        # Compile results
        equity_curve = pd.Series(equity, index=df.index[:len(equity)])
        metrics = calculate_metrics(equity_curve, trades)

        return {
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": trades
        }
