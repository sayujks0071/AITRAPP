import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from packages.strategy_foundry.factory.grammar import StrategySpec, StrategyType, FilterType, ExitType
from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class BacktestEngine:
    def __init__(self, cost_bps=5.0, slippage_bps=5.0):
        self.cost_pct = cost_bps / 10000.0
        self.slippage_pct = slippage_bps / 10000.0
        self.calc = VectorIndicatorCalculator()

    def run(self, df: pd.DataFrame, spec: StrategySpec) -> Dict[str, Any]:
        """
        Run backtest for a single candidate on provided data.
        Returns metrics and trades.
        """
        # Working copy
        data = df.copy()

        # 1. Prepare Indicators
        self._prepare_indicators(data, spec)

        # 2. Generate Entry Signals
        self._generate_entry_signal(data, spec)

        # 3. Simulate Execution
        trades, equity_curve, final_position = self._simulate(data, spec)

        # 4. Calculate Metrics
        trades_df = pd.DataFrame(trades)

        # Calculate daily returns from equity curve for Sharpe/Drawdown
        # Resample to daily close
        daily_equity = equity_curve.resample('D').last().dropna()
        daily_returns = daily_equity.pct_change().dropna()

        metrics = calculate_metrics(trades_df, daily_returns)

        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "final_position": final_position
        }

    def _prepare_indicators(self, df: pd.DataFrame, spec: StrategySpec):
        # Entry Params
        st_params = spec["strategy_params"]
        st_type = spec["strategy_type"]

        if st_type == StrategyType.BREAKOUT_DONCHIAN.value:
            p = st_params["period"]
            df["dc_upper"], df["dc_lower"] = self.calc.donchian(df, period=p)

        elif st_type == StrategyType.TREND_EMA_CROSS.value:
            df["ema_fast"] = self.calc.ema(df["close"], period=st_params["fast_period"])
            df["ema_slow"] = self.calc.ema(df["close"], period=st_params["slow_period"])

        elif st_type == StrategyType.MEAN_REV_RSI.value:
            df["rsi"] = self.calc.rsi(df, period=st_params["period"])

        elif st_type == StrategyType.MEAN_REV_BB.value:
            df["bb_upper"], df["bb_lower"], _ = self.calc.bollinger_bands(df["close"], period=st_params["period"], std=st_params["std"])

        elif st_type == StrategyType.VOL_EXPANSION_ATR.value:
            df["atr"] = self.calc.atr(df, period=st_params["period"])

        elif st_type == StrategyType.SUPERTREND_FOLLOW.value:
            df["supertrend"], df["st_dir"] = self.calc.supertrend(df, period=st_params["period"], multiplier=st_params["multiplier"])

        # Filter Params
        ft_type = spec["filter_type"]
        ft_params = spec["filter_params"]

        if ft_type == FilterType.REGIME_EMA.value:
            df["filter_ema"] = self.calc.sma(df["close"], period=ft_params["period"]) # Using SMA as proxy for long term trend if desired, or EMA
        elif ft_type == FilterType.VOLATILITY_ADX.value:
            df["adx"] = self.calc.adx(df, period=ft_params["period"])
        elif ft_type == FilterType.RSI_FILTER.value:
            if "rsi" not in df.columns:
                df["rsi"] = self.calc.rsi(df, period=ft_params["period"])

        # ATR for Exits (always calculated if not present)
        if "atr" not in df.columns:
             df["atr"] = self.calc.atr(df, period=14) # Default 14 for risk if not specified

    def _generate_entry_signal(self, df: pd.DataFrame, spec: StrategySpec):
        # Initialize
        df["entry_long"] = False

        st_type = spec["strategy_type"]
        st_params = spec["strategy_params"]

        # Base Entry Logic
        if st_type == StrategyType.BREAKOUT_DONCHIAN.value:
            # Breakout: Close > DC Upper (prev bar)
            # Actually Donchian usually excludes current bar, but let's assume 'dc_upper' is calculated including current.
            # So breakout is Close > Shifted DC Upper.
            # Packages core donchian uses rolling max.
            # We need to compare Close to Previous High Max.
            # dc_upper in core includes current high.
            # So Signal: Close > dc_upper.shift(1)
            df["entry_long"] = df["close"] > df["dc_upper"].shift(1)

        elif st_type == StrategyType.TREND_EMA_CROSS.value:
            # Crossover
            df["entry_long"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))

        elif st_type == StrategyType.MEAN_REV_RSI.value:
            # RSI < Oversold
            df["entry_long"] = df["rsi"] < st_params["oversold"]

        elif st_type == StrategyType.MEAN_REV_BB.value:
            # Close < Lower Band
            df["entry_long"] = df["close"] < df["bb_lower"]

        elif st_type == StrategyType.VOL_EXPANSION_ATR.value:
            # Close > High[1] + ATR[1]
            df["entry_long"] = df["close"] > (df["high"].shift(1) + df["atr"].shift(1))

        elif st_type == StrategyType.SUPERTREND_FOLLOW.value:
            # Supertrend dir flip -1 to 1
            df["entry_long"] = (df["st_dir"] == 1) & (df["st_dir"].shift(1) == -1)

        # Apply Filters
        ft_type = spec["filter_type"]
        ft_params = spec["filter_params"]

        if ft_type == FilterType.REGIME_EMA.value:
            df["entry_long"] = df["entry_long"] & (df["close"] > df["filter_ema"])

        elif ft_type == FilterType.VOLATILITY_ADX.value:
            df["entry_long"] = df["entry_long"] & (df["adx"] > ft_params["threshold"])

        elif ft_type == FilterType.RSI_FILTER.value:
            # Check RSI if not already the main strategy
            if "rsi" in df.columns:
                df["entry_long"] = df["entry_long"] & (df["rsi"] < ft_params["max_val"])

    def _simulate(self, df: pd.DataFrame, spec: StrategySpec) -> Tuple[List, pd.Series, int]:
        trades = []
        equity = 100000.0

        # Performance Optimization: Use numpy array for equity tracking instead of Series
        n = len(df)
        equity_values = np.full(n, np.nan, dtype=np.float64)

        position = 0 # 0 or 1
        entry_price = 0.0
        entry_time = None
        sl_price = 0.0
        tp_price = 0.0
        bars_held = 0

        ex_type = spec["exit_type"]
        ex_params = spec["exit_params"]
        sl_mult = ex_params["sl_mult"]
        tp_mult = ex_params["tp_mult"]

        # Mandatory Close
        close_time_str = spec.get("session_close_time", "15:25")
        close_hour, close_minute = map(int, close_time_str.split(":"))

        # Pre-convert to numpy for speed
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        atrs = df["atr"].values
        entries = df["entry_long"].values
        times = df.index

        # Pre-compute time checks to avoid repeated attribute access
        times_hours = times.hour
        times_minutes = times.minute

        for i in range(n - 1): # Stop at n-1 to execute next open
            current_time = times[i]
            equity_values[i] = equity # Mark to market roughly

            # 1. Manage Existing Position
            if position > 0:
                bars_held += 1
                exit_price = None
                exit_reason = ""

                # Check Intraday Force Close
                # Use pre-computed hour/minute arrays for speed
                curr_h = times_hours[i]
                curr_m = times_minutes[i]

                if curr_h > close_hour or (curr_h == close_hour and curr_m >= close_minute):
                    exit_price = opens[i] # Exit at Open of this bar if we passed time (or close of prev, simplified to open of current)
                    exit_reason = "SESSION_CLOSE"

                # Check SL/TP (Hit within bar)
                elif lows[i] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif highs[i] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"

                # Check Time Stop
                elif ex_type == ExitType.TIME_BASED.value and bars_held >= ex_params["max_bars"]:
                    exit_price = opens[i+1] # Exit next open
                    exit_reason = "TIME_STOP"

                # Check Trailing
                if ex_type == ExitType.TRAILING_ATR.value and exit_price is None:
                    # Update SL
                    new_sl = closes[i] - (atrs[i] * sl_mult)
                    if new_sl > sl_price:
                        sl_price = new_sl

                # Execute Exit
                if exit_price is not None:
                    # Apply costs
                    # Exit Price adjustment for slippage
                    eff_exit_price = exit_price * (1 - self.slippage_pct)

                    pnl_pct = (eff_exit_price - entry_price) / entry_price
                    # Deduct transaction costs (bps on notional)
                    # Cost applied on both legs approx 2 * cost_pct
                    pnl_pct -= (2 * self.cost_pct)

                    pnl = equity * pnl_pct # Fixed fractional of current equity? Or fixed initial? Let's use compounding.

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": eff_exit_price,
                        "pnl": pnl,
                        "return_pct": pnl_pct,
                        "reason": exit_reason
                    })

                    equity += pnl
                    position = 0
                    bars_held = 0
                    continue # Position closed, can't enter same bar (simplified)

            # 2. Check Entry
            # Only enter if flat and market is not about to close
            # Use pre-computed time arrays
            curr_h = times_hours[i]
            curr_m = times_minutes[i]
            time_ok = (curr_h < close_hour) or (curr_h == close_hour and curr_m < close_minute - 15)

            if position == 0 and entries[i] and time_ok:
                # Enter next Open
                entry_price_raw = opens[i+1]
                entry_price = entry_price_raw * (1 + self.slippage_pct)
                entry_time = times[i+1]
                position = 1
                bars_held = 0

                # Set Initial Stops
                atr_val = atrs[i] # Use signal bar ATR
                sl_price = entry_price_raw - (atr_val * sl_mult)
                tp_price = entry_price_raw + (atr_val * tp_mult)

        # Fill last equity
        equity_values[-1] = equity

        # Convert back to Series
        equity_series = pd.Series(equity_values, index=df.index)
        return trades, equity_series, position
