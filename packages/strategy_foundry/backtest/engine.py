import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import structlog
from datetime import time, datetime

from packages.strategy_foundry.factory.grammar import StrategySpec, EntryType
from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator
from packages.strategy_foundry.backtest.metrics import calculate_metrics, annualized_metrics

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, costs: Dict[str, Any] = None):
        self.initial_capital = initial_capital
        self.costs = costs or {"slippage_bps": 5.0, "brokerage_per_order": 20.0, "tax_bps": 3.0}
        self.indicator_calc = VectorIndicatorCalculator()

    def _generate_entry_signals(self, df: pd.DataFrame, spec: StrategySpec) -> np.ndarray:
        """
        Generate boolean array for entry signals (1 for Buy, 0 for None)
        """
        signal = np.zeros(len(df), dtype=int)

        if spec.entry_logic == EntryType.RSI_REVERSION.value:
            p = spec.entry_params.get("period", 14)
            t = spec.entry_params.get("threshold", 30)
            calc = VectorIndicatorCalculator(rsi_period=p)
            rsi = calc.rsi_series(df)
            signal = np.where(rsi < t, 1, 0)

        elif spec.entry_logic == EntryType.RSI_MOMENTUM.value:
            p = spec.entry_params.get("period", 14)
            t = spec.entry_params.get("threshold", 60)
            calc = VectorIndicatorCalculator(rsi_period=p)
            rsi = calc.rsi_series(df)
            signal = np.where(rsi > t, 1, 0)

        elif spec.entry_logic == EntryType.EMA_CROSS.value:
            fast = spec.entry_params.get("fast_period", 9)
            slow = spec.entry_params.get("slow_period", 21)
            calc = VectorIndicatorCalculator(ema_fast=fast, ema_slow=slow)
            ema_f = calc.ema_series(df["close"], fast)
            ema_s = calc.ema_series(df["close"], slow)
            # Cross above
            # (ema_f > ema_s) & (prev_ema_f <= prev_ema_s)
            prev_f = np.roll(ema_f, 1)
            prev_s = np.roll(ema_s, 1)
            signal = np.where((ema_f > ema_s) & (prev_f <= prev_s), 1, 0)

        elif spec.entry_logic == EntryType.DONCHIAN_BREAKOUT.value:
            p = spec.entry_params.get("period", 20)
            calc = VectorIndicatorCalculator()
            upper, lower = calc.donchian_series(df, period=p)
            # Close > prev upper
            prev_upper = np.roll(upper, 1)
            signal = np.where(df["close"] > prev_upper, 1, 0)

        elif spec.entry_logic == EntryType.SUPERTREND_FOLLOW.value:
            p = spec.entry_params.get("period", 10)
            m = spec.entry_params.get("multiplier", 3.0)
            calc = VectorIndicatorCalculator(supertrend_period=p, supertrend_multiplier=m)
            st, direction = calc.supertrend_series(df)
            # Buy when direction flips to 1
            prev_dir = np.roll(direction, 1)
            signal = np.where((direction == 1) & (prev_dir == -1), 1, 0)

        elif spec.entry_logic == EntryType.BB_REVERSION.value:
            p = spec.entry_params.get("period", 20)
            std = spec.entry_params.get("std", 2.0)
            calc = VectorIndicatorCalculator(bb_period=p, bb_std=std)
            u, m, l = calc.bollinger_bands_series(df)
            signal = np.where(df["close"] < l, 1, 0)

        return signal

    def run(self, spec: StrategySpec, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {}

        # 1. Calc ATR for stops
        calc = VectorIndicatorCalculator(atr_period=14)
        atr = calc.atr_series(df)

        # 2. Generate signals
        entry_signals = self._generate_entry_signals(df, spec)

        # 3. Iterative Execution
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        timestamps = df["timestamp"].values # numpy datetime64

        # Optimization: Pre-compute session close checks
        # We want to be flat BY 15:25. So if the current bar >= 15:25, we must exit.
        # Assuming bars are labelled by open time.
        # If current bar is 15:25, it closes at 15:30. Exiting at close of 15:25 is flat by 15:30.
        # This is acceptable for intraday "End of Day".
        times = df["timestamp"].dt.strftime("%H:%M").values
        close_time = spec.session_close_time
        should_close_session = (times >= close_time)

        position = 0
        entry_price = 0.0
        entry_idx = 0
        sl_price = 0.0
        tp_price = 0.0

        trades = []
        equity = [self.initial_capital]

        n = len(df)

        for i in range(1, n): # Start from 1 to have prev bar
            # 1. Check Exit for existing position
            if position != 0:
                exit_reason = None
                exit_price = 0.0

                # OHLC of current bar
                curr_open = opens[i]
                curr_high = highs[i]
                curr_low = lows[i]
                curr_close = closes[i]

                # Check Stop Loss (hit at Low)
                if position > 0:
                    if curr_low <= sl_price:
                        exit_price = min(curr_open, sl_price) # If gap down, exit at open
                        # Slippage
                        exit_price -= (exit_price * self.costs["slippage_bps"] / 10000)
                        exit_reason = "SL"

                    # Check Take Profit
                    elif curr_high >= tp_price:
                        exit_price = max(curr_open, tp_price)
                        # Slippage
                        exit_price -= (exit_price * self.costs["slippage_bps"] / 10000)
                        exit_reason = "TP"

                    # Check Time Exit
                    elif spec.time_exit_bars and (i - entry_idx) >= spec.time_exit_bars:
                        exit_price = curr_open
                        exit_price -= (exit_price * self.costs["slippage_bps"] / 10000)
                        exit_reason = "Time"

                    # Check Session Close
                    elif should_close_session[i]:
                        exit_price = curr_close # Exit at close
                        exit_price -= (exit_price * self.costs["slippage_bps"] / 10000)
                        exit_reason = "Session"

                if exit_reason:
                    # Execute Exit
                    # Assuming full capital compounding
                    shares = equity[-1] / entry_price
                    pnl = (exit_price - entry_price) * shares

                    # Deduct brokerage
                    pnl -= self.costs["brokerage_per_order"] * 2

                    # Deduct tax (approx on turnover)
                    turnover = (entry_price + exit_price) * shares
                    pnl -= turnover * self.costs["tax_bps"] / 10000

                    equity_val = equity[-1] + pnl
                    equity.append(equity_val)

                    trades.append({
                        "entry_time": timestamps[entry_idx],
                        "exit_time": timestamps[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "return_pct": (exit_price - entry_price) / entry_price,
                        "reason": exit_reason,
                        "duration": i - entry_idx
                    })

                    position = 0
                    continue
                else:
                    equity.append(equity[-1]) # No change

            else:
                equity.append(equity[-1])

            # 2. Check Entry
            # Signal from previous bar close (index i-1) triggers entry at Open of i
            if position == 0:
                # Don't enter if session is closing
                if should_close_session[i]:
                    continue

                if entry_signals[i-1] == 1:
                    # Buy
                    entry_price = opens[i]
                    # Add slippage
                    entry_price += (entry_price * self.costs["slippage_bps"] / 10000)

                    position = 1
                    entry_idx = i

                    # Set SL/TP based on ATR of previous bar (i-1)
                    curr_atr = atr[i-1]
                    if np.isnan(curr_atr):
                        curr_atr = entry_price * 0.01 # Fallback 1%

                    sl_dist = curr_atr * spec.stop_loss_atr
                    tp_dist = curr_atr * spec.take_profit_atr

                    sl_price = entry_price - sl_dist
                    tp_price = entry_price + tp_dist

        # End of loop

        trades_df = pd.DataFrame(trades)
        equity_curve = pd.Series(equity, index=df["timestamp"][:len(equity)])

        # Calculate Metrics
        metrics = calculate_metrics(trades_df, self.initial_capital)

        # Add Time-Series metrics from Equity Curve
        # Resample to daily to get standard Sharpe
        if not equity_curve.empty:
            # Forward fill equity for intraday to get end-of-day values
            daily_equity = equity_curve.resample('B').last().ffill()
            daily_returns = daily_equity.pct_change().dropna()
            ts_metrics = annualized_metrics(daily_returns)
            metrics.update(ts_metrics)

        metrics["final_equity"] = equity[-1]

        current_state = {
            "position": position,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "entry_time": timestamps[entry_idx] if position != 0 else None
        }

        return {
            "metrics": metrics,
            "trades": trades_df,
            "equity_curve": equity_curve,
            "current_state": current_state
        }
