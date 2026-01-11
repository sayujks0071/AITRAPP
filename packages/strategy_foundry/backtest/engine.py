"""Backtest Engine"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import structlog

from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, costs_bps: float = 2.0, spread_bps: float = 1.0):
        self.costs_pct = (costs_bps + spread_bps) / 10000.0

    def run(self, df: pd.DataFrame, strategy: StrategyConfig) -> Dict[str, Any]:
        """
        Run backtest for a single strategy on provided data.
        """
        if df.empty:
            return {"trades": [], "metrics": {}}

        # 1. Calculate Indicators required by strategy
        indicators = self._calc_indicators(df, strategy)

        # 2. Generate Signals
        signals = self._generate_signals(df, indicators, strategy)

        # 3. Simulate Execution
        trades, equity_curve = self._simulate(df, signals, strategy)

        # 4. Compute Metrics
        metrics = calculate_metrics(trades, equity_curve, df)

        return {
            "trades": trades,
            "metrics": metrics,
            "equity_curve": equity_curve
        }

    def _calc_indicators(self, df: pd.DataFrame, strategy: StrategyConfig) -> Dict[str, np.ndarray]:
        inds = {}
        # Always calc ATR for stops
        inds["atr"] = VectorizedIndicators.atr(df["high"].values, df["low"].values, df["close"].values, 14)

        # Parse rules to see what else we need
        all_rules = strategy.entry_rules + strategy.exit_rules + strategy.filters
        for rule in all_rules:
            if "EMA" in rule.type:
                p = rule.params.get("period") or rule.params.get("fast")
                if p: inds[f"ema_{p}"] = VectorizedIndicators.ema(df["close"].values, p)
                p2 = rule.params.get("slow")
                if p2: inds[f"ema_{p2}"] = VectorizedIndicators.ema(df["close"].values, p2)

            if "RSI" in rule.type:
                p = rule.params.get("period", 14)
                inds[f"rsi_{p}"] = VectorizedIndicators.rsi(df["close"].values, p)

            if "BB" in rule.type:
                p = rule.params.get("period", 20)
                std = rule.params.get("std", 2.0)
                u, m, l = VectorizedIndicators.bollinger_bands(df["close"].values, p, std)
                inds[f"bb_upper_{p}"] = u
                inds[f"bb_lower_{p}"] = l

            if "DONCHIAN" in rule.type:
                p = rule.params.get("period", 20)
                u, l = VectorizedIndicators.donchian(df["high"].values, df["low"].values, p)
                inds[f"dc_upper_{p}"] = u
                inds[f"dc_lower_{p}"] = l

        return inds

    def _generate_signals(self, df: pd.DataFrame, inds: Dict[str, np.ndarray], strategy: StrategyConfig) -> np.ndarray:
        """
        Generate raw entry signals (-1, 0, 1).
        Execution logic (stops, exits) handles the rest.
        """
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        times = df.index

        entries = np.zeros(len(df), dtype=int)

        # Apply Filters First
        trade_allowed = np.ones(len(df), dtype=bool)

        for rule in strategy.filters:
            if rule.type == "FILTER_TIME_NO_TRADE":
                # Convert time strings to minutes from midnight for comparison or just use string comp if format matches
                # Simpler: string comparison on time
                current_times = times.strftime("%H:%M")
                start = rule.params["start"]
                end = rule.params["end"]
                mask = (current_times >= start) & (current_times <= end)
                trade_allowed[mask] = False

        # Apply Entry Rules
        for rule in strategy.entry_rules:
            signal = np.zeros(len(df), dtype=int)

            if rule.type == "BREAKOUT_ORB":
                # This requires daily context which is hard in pure arrays without grouping
                # Simplified: Assume we have pre-calced ORB levels or calculate on fly?
                # For vectorization, we can group by date.
                # Actually, let's skip complex vectorization for ORB and do it in loop or simplified
                # For now, placeholder for ORB: skip or implement later.
                # Let's implement EMA Cross as baseline
                pass

            elif rule.type == "TREND_EMA_CROSS":
                fast = inds[f"ema_{rule.params['fast']}"]
                slow = inds[f"ema_{rule.params['slow']}"]
                # Cross over
                cross_up = (fast > slow) & (np.roll(fast, 1) <= np.roll(slow, 1))
                signal[cross_up] = 1

            elif rule.type == "MEANREV_RSI":
                rsi = inds[f"rsi_{rule.params['period']}"]
                # Buy if RSI < lower
                signal[rsi < rule.params['lower']] = 1

            elif rule.type == "BREAKOUT_DONCHIAN":
                u = inds[f"dc_upper_{rule.params['period']}"]
                # Buy if close > upper (shifted by 1 to avoid lookahead? Donchian usually includes current bar, so breakout is > prev max)
                # Standard Donchian: Upper Band is Max(High, n). Breakout is Close > Upper.
                # Usually we want Close > Ref(Upper, 1)
                prev_u = np.roll(u, 1)
                signal[closes > prev_u] = 1

            # Combine with AND logic if multiple entry rules?
            # Usually grammar selects ONE entry block.
            entries = np.where(signal != 0, signal, entries)

        # Apply filters
        entries[~trade_allowed] = 0

        return entries

    def _simulate(self, df: pd.DataFrame, entry_signals: np.ndarray, strategy: StrategyConfig):
        """
        Event-driven simulation loop over bars.
        """
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df.index
        atr = VectorizedIndicators.atr(highs, lows, closes, 14)

        trades = []
        equity_curve = [1.0] # start at 1.0 (normalized)

        position = 0 # 0, 1 (long), -1 (short - disabled for now)
        entry_price = 0.0
        entry_time = None
        stop_price = 0.0
        target_price = 0.0
        bars_held = 0

        # Parse exit params
        stop_atr_mult = 2.0
        target_rr = 0.0
        time_limit = 0

        for rule in strategy.exit_rules:
            if rule.type == "STOP_ATR":
                stop_atr_mult = rule.params["multiplier"]
            if rule.type == "TARGET_FIXED":
                target_rr = rule.params["risk_reward"]
            if rule.type == "STOP_TIME":
                time_limit = rule.params["bars"]

        curr_equity = 1.0

        for i in range(1, len(df)):
            # Market Close check (Hard Exit)
            current_time_str = times[i].strftime("%H:%M")
            is_market_closing = current_time_str >= "15:20"

            # Check Exit if in position
            if position != 0:
                bars_held += 1
                exit_price = 0.0
                reason = ""

                # 1. Market Close
                if is_market_closing:
                    exit_price = opens[i] # Exit at open of closing bar (approx) or close?
                    # "All positions flat by 15:25". If this bar is 15:20-15:25, exit at open.
                    exit_price = opens[i]
                    reason = "SESSION"

                # 2. Stop Loss
                elif lows[i] <= stop_price:
                    exit_price = stop_price # Assume filled at stop (slippage added later)
                    reason = "STOP"

                # 3. Target
                elif target_rr > 0 and highs[i] >= target_price:
                    exit_price = target_price
                    reason = "TARGET"

                # 4. Time Stop
                elif time_limit > 0 and bars_held >= time_limit:
                    exit_price = opens[i]
                    reason = "TIME"

                if exit_price > 0:
                    # Execute Exit
                    # Apply slippage/costs
                    # PnL % = (Exit - Entry) / Entry
                    raw_ret = (exit_price - entry_price) / entry_price

                    # Cost: bps per side.
                    # total cost = 2 * cost_pct
                    net_ret = raw_ret - (2 * self.costs_pct)

                    # If stopped out, use worse price (slippage already in costs? No, slippage is extra usually)
                    # We added slippage to cost_pct in __init__.

                    curr_equity *= (1 + net_ret)

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": times[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return": net_ret,
                        "reason": reason,
                        "bars": bars_held
                    })

                    position = 0
                    bars_held = 0

            # Check Entry (if flat and not closing)
            if position == 0 and not is_market_closing:
                # Signal calculated at i-1 close, enter at i open
                sig = entry_signals[i-1]
                if sig == 1:
                    position = 1
                    entry_price = opens[i]
                    entry_time = times[i]

                    # Set Stops/Targets
                    current_atr = atr[i-1] if not np.isnan(atr[i-1]) else (entry_price * 0.01)
                    stop_dist = current_atr * stop_atr_mult
                    stop_price = entry_price - stop_dist

                    if target_rr > 0:
                        target_price = entry_price + (stop_dist * target_rr)

            equity_curve.append(curr_equity)

        return trades, pd.Series(equity_curve, index=df.index[:len(equity_curve)])
