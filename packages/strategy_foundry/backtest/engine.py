import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import structlog
from packages.strategy_foundry.factory.grammar import StrategySpec
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators as VI
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = structlog.get_logger(__name__)

class BacktestEngine:
    """Event-driven backtest engine tailored for intraday strategies"""

    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0, costs: Dict = None):
        self.data = data
        self.initial_capital = initial_capital
        self.costs = costs or {"bps_per_side": 5.0, "slippage_bps": 5.0}

    def _compute_indicators(self, strategy: StrategySpec) -> Dict[str, pd.Series]:
        """Pre-compute all indicators required by the strategy blocks"""
        indicators = {}

        # We need a unique key for each indicator param set to avoid re-computation
        for block in strategy.blocks:
            if block.type == "donchian_breakout":
                p = block.params["period"]
                if f"donchian_{p}_upper" not in indicators:
                    u, l = VI.donchian(self.data["High"], self.data["Low"], p)
                    indicators[f"donchian_{p}_upper"] = u
                    indicators[f"donchian_{p}_lower"] = l

            elif block.type == "ema_cross":
                f, s = block.params["fast"], block.params["slow"]
                if f"ema_{f}" not in indicators:
                    indicators[f"ema_{f}"] = VI.ema(self.data["Close"], f)
                if f"ema_{s}" not in indicators:
                    indicators[f"ema_{s}"] = VI.ema(self.data["Close"], s)

            elif block.type == "rsi_long":
                p = block.params["period"]
                if f"rsi_{p}" not in indicators:
                    indicators[f"rsi_{p}"] = VI.rsi(self.data["Close"], p)

            elif block.type == "bb_breakout":
                p = block.params["period"]
                std = block.params["std_dev"]
                key = f"bb_{p}_{std}"
                if f"{key}_upper" not in indicators:
                    u, m, l = VI.bollinger_bands(self.data["Close"], p, std)
                    indicators[f"{key}_upper"] = u
                    indicators[f"{key}_lower"] = l

            elif block.type == "atr_stop":
                p = block.params["period"]
                if f"atr_{p}" not in indicators:
                    indicators[f"atr_{p}"] = VI.atr(self.data["High"], self.data["Low"], self.data["Close"], p)

            elif block.type == "adx_filter":
                p = block.params["period"]
                if f"adx_{p}" not in indicators:
                    indicators[f"adx_{p}"] = VI.adx(self.data["High"], self.data["Low"], self.data["Close"], p)

            elif block.type == "ema_trend_filter":
                p = block.params["period"]
                if f"ema_{p}" not in indicators:
                    indicators[f"ema_{p}"] = VI.ema(self.data["Close"], p)

        return indicators

    def _check_entry(self, i: int, strategy: StrategySpec, indicators: Dict[str, pd.Series]) -> bool:
        """Check if entry conditions are met at index i (using data up to i)"""
        # Entry logic: All entry blocks must signal True? Or any?
        # Usually strategy has 1 entry block.
        # If multiple entry blocks, we can treat them as OR or AND.
        # Given the grammar structure (list of blocks), let's assume ALL entry blocks must be True (AND)
        # but the generator currently produces only 1 entry block.

        triggered = False
        has_entry_block = False

        for block in strategy.blocks:
            if block.type == "donchian_breakout":
                has_entry_block = True
                p = block.params["period"]
                # Close > Upper of PREVIOUS bar (i is current bar which just closed)
                # Wait, signals are calculated on CLOSE of i.
                # Breakout usually implies Close[i] > DonchianUpper[i-1] (the channel formed by previous bars)
                # Or DonchianUpper[i] (which includes i)?
                # Standard Donchian excludes current bar for signal, so it's max(High[i-p:i]).
                # My implementation of rolling max includes current row.
                # So `indicators[...][i]` is max of i-p+1 to i.
                # Breakout of *previous* N days high means Close[i] > DonchianUpper[i-1].

                # Careful with indexing. indicators are Series with same index as data.
                # i is integer index.
                if i == 0: continue

                # We access via .iloc
                upper_prev = indicators[f"donchian_{p}_upper"].iloc[i-1]
                close_curr = self.data["Close"].iloc[i]

                if close_curr > upper_prev:
                    triggered = True
                else:
                    return False # AND condition

            elif block.type == "ema_cross":
                has_entry_block = True
                f, s = block.params["fast"], block.params["slow"]
                # Crossover: Fast[i] > Slow[i] AND Fast[i-1] <= Slow[i-1]
                if i == 0: continue

                fast_curr = indicators[f"ema_{f}"].iloc[i]
                slow_curr = indicators[f"ema_{s}"].iloc[i]
                fast_prev = indicators[f"ema_{f}"].iloc[i-1]
                slow_prev = indicators[f"ema_{s}"].iloc[i-1]

                if fast_curr > slow_curr and fast_prev <= slow_prev:
                    triggered = True
                else:
                    return False

            elif block.type == "rsi_long":
                has_entry_block = True
                p = block.params["period"]
                thresh = block.params["threshold"]
                # Mean reversion: RSI < Threshold (Oversold)
                rsi_val = indicators[f"rsi_{p}"].iloc[i]
                if rsi_val < thresh:
                    triggered = True
                else:
                    return False

            elif block.type == "bb_breakout":
                has_entry_block = True
                p = block.params["period"]
                std = block.params["std_dev"]
                key = f"bb_{p}_{std}"
                # Close > Upper
                upper = indicators[f"{key}_upper"].iloc[i] # Current upper (expanded)
                # Or previous upper? Usually breakout is against the bands.
                # If we use current upper, and price pushes it up, it's valid.
                if self.data["Close"].iloc[i] > upper:
                    triggered = True
                else:
                    return False

        # Check filters
        for block in strategy.blocks:
            if block.type == "adx_filter":
                p = block.params["period"]
                thresh = block.params["threshold"]
                adx_val = indicators[f"adx_{p}"].iloc[i]
                if adx_val < thresh: # Filter out if trend is weak? Or filter out if ADX < X (chop)?
                    # Usually ADX > 20 means trend. If entry is breakout, we want ADX > 20.
                    # If entry is mean reversion (rsi_long), we might want ADX < 20 (ranging).
                    # For now assume "Trend Filter" behavior: Must be trending.
                    return False

            elif block.type == "ema_trend_filter":
                p = block.params["period"]
                ema_val = indicators[f"ema_{p}"].iloc[i]
                # Filter: Price > EMA (Uptrend)
                if self.data["Close"].iloc[i] < ema_val:
                    return False

        return triggered and has_entry_block

    def run(self, strategy: StrategySpec) -> Dict[str, Any]:
        indicators = self._compute_indicators(strategy)
        trades = []

        # State
        position = 0 # 1 for Long, 0 for Flat
        entry_price = 0.0
        entry_time = None
        stop_price = 0.0
        target_price = 0.0
        bars_held = 0

        # Identify blocks
        exit_blocks = [b for b in strategy.blocks if b.type in ["atr_stop", "time_stop", "profit_target"]]

        # Pre-calc specific indicators for exits to avoid lookup in loop
        # But we need them dynamically based on entry time for trailing?
        # Simple stop logic: fixed at entry.

        dates = self.data.index
        opens = self.data["Open"].values
        highs = self.data["High"].values
        lows = self.data["Low"].values
        closes = self.data["Close"].values
        times = dates.time

        n = len(self.data)

        # Find ATR block for stop calculation
        atr_block = next((b for b in exit_blocks if b.type == "atr_stop"), None)
        profit_block = next((b for b in exit_blocks if b.type == "profit_target"), None)
        time_block = next((b for b in exit_blocks if b.type == "time_stop"), None)

        for i in range(1, n):
            # Check Exits if Long
            if position == 1:
                bars_held += 1
                exit_signal = False
                exit_price = 0.0
                exit_reason = ""

                current_time = times[i]

                # 1. Check Stop Loss
                if stop_price > 0:
                    if lows[i] < stop_price:
                        # Hit stop
                        exit_signal = True
                        # Slippage logic:
                        # If Open < Stop, we gapped down -> Exit at Open
                        # Else -> Exit at Stop
                        if opens[i] < stop_price:
                            exit_price = opens[i]
                        else:
                            exit_price = stop_price
                        exit_reason = "SL"

                # 2. Check Profit Target
                if not exit_signal and target_price > 0:
                    if highs[i] > target_price:
                        # Hit target
                        exit_signal = True
                        # If Open > Target, gap up -> Exit at Open
                        # Else -> Exit at Target
                        if opens[i] > target_price:
                            exit_price = opens[i]
                        else:
                            exit_price = target_price
                        exit_reason = "TP"

                # 3. Check Time Stop
                if not exit_signal and time_block:
                    if bars_held >= time_block.params["bars"]:
                        exit_signal = True
                        exit_price = closes[i]
                        exit_reason = "Time"

                # 4. Intraday EOD Force Close (15:25)
                # Assuming 15:25 is close enough to end of data if processed correctly.
                # If current bar time >= 15:25
                if not exit_signal:
                    if current_time.hour == 15 and current_time.minute >= 25:
                        exit_signal = True
                        exit_price = closes[i]
                        exit_reason = "EOD"

                if exit_signal:
                    # Execute Exit
                    pnl = (exit_price - entry_price)
                    # Apply costs
                    # bps per side applied to notional.
                    # pnl_net = pnl - costs
                    # cost = (entry_price * bps + exit_price * bps) / 10000
                    cost = (entry_price + exit_price) * self.costs["bps_per_side"] / 10000.0
                    slippage = (entry_price + exit_price) * self.costs["slippage_bps"] / 10000.0

                    pnl_net = pnl - cost - slippage

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": dates[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl_net, # Assuming 1 unit. Metrics will scale.
                        "reason": exit_reason,
                        "bars_held": bars_held
                    })

                    position = 0
                    continue # Finished this bar logic

            # Check Entry if Flat (and not end of day)
            # Don't enter after 15:00
            if position == 0:
                if times[i].hour >= 15:
                    continue

                # Signal is based on data up to i-1 (completed bar)
                # But we use indicators calculated on series.
                # _check_entry uses i-1 internally?
                # No, _check_entry(i) checks if condition met at index i.
                # We want to check if condition met at i-1, to enter at Open[i].

                if self._check_entry(i-1, strategy, indicators):
                    # Enter Long
                    position = 1
                    entry_price = opens[i]
                    entry_time = dates[i]
                    bars_held = 0

                    # Set Stop/Target
                    # ATR based
                    current_atr = 0.0
                    if atr_block:
                        p = atr_block.params["period"]
                        mult = atr_block.params["multiplier"]
                        current_atr = indicators[f"atr_{p}"].iloc[i-1] # ATR from prev bar
                        stop_price = entry_price - (current_atr * mult)
                    else:
                        stop_price = 0.0 # No stop? Dangerous.

                    if profit_block and current_atr > 0:
                        rr = profit_block.params["rr"]
                        risk = entry_price - stop_price
                        target_price = entry_price + (risk * rr)
                    else:
                        target_price = 0.0

        metrics = calculate_metrics(trades, self.initial_capital)

        open_pos_info = None
        if position == 1:
            open_pos_info = {
                "entry_time": entry_time,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "bars_held": bars_held,
                "pnl_unrealized": float(closes[-1] - entry_price)
            }

        return {"metrics": metrics, "trades": trades, "open_position": open_pos_info}
