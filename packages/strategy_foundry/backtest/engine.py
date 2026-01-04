"""
Backtest Engine
Intraday capable with session flattening.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from packages.strategy_foundry.adapters.core_indicators import Indicators
from packages.strategy_foundry.adapters.core_market_hours import MarketHours

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, strategy_config: Dict, cost_config: Dict = None):
        self.data = data.copy()
        self.strategy = strategy_config
        self.costs = cost_config or {"all_in_cost_bps_per_side": 3.0, "slippage_bps_per_side": 2.0}
        self.results = {}

    def run(self):
        df = self.data
        if df.empty:
            return None

        # 1. Compute Indicators
        self._compute_indicators(df)

        # 2. Generate Signals
        signals = self._generate_signals(df)

        # 3. Simulate Execution
        trades = self._simulate_execution(df, signals)

        # 4. Compute Metrics
        metrics = self._compute_metrics(trades, df)

        return {
            "trades": trades,
            "metrics": metrics,
            "equity_curve": metrics.get("equity_curve")
        }

    def _compute_indicators(self, df):
        # Entry params
        entry = self.strategy["entry"]
        entry_type = list(entry.keys())[0] if isinstance(entry, dict) and entry else ""
        if not entry_type and "type" in entry: entry_type = entry["type"] # Handle varying structures if any

        # Helper to safely get param
        def get_p(d, k, default): return d.get(k, default) if isinstance(d, dict) else default

        # Pre-compute common ones if needed or lazily
        # Here we just compute what is needed based on config

        # TODO: Refactor this to be more dynamic based on registry, but manual dispatch is fine for now

        if "rsi" in str(self.strategy):
            df["rsi"] = Indicators.rsi(df["close"], 14)
        if "atr" in str(self.strategy) or "supertrend" in str(self.strategy):
             df["atr"] = Indicators.atr(df["high"], df["low"], df["close"], 14)

        entry_params = entry # Assuming direct dict

        if "trend_ema_cross" in self.strategy.get("id", "") or "trend_ema_cross" in str(self.strategy):
             # Actually, we should parse the strategy structure properly
             pass

        # We will parse strictly based on the grammar structure
        # Entry
        e_conf = self.strategy.get("entry", {})
        e_type = next(iter(e_conf)) if e_conf else None
        if e_type == "trend_ema_cross":
            p = e_conf[e_type]
            df["ema_fast"] = Indicators.ema(df["close"], p["fast"])
            df["ema_slow"] = Indicators.ema(df["close"], p["slow"])
        elif e_type == "trend_supertrend":
            p = e_conf[e_type]
            df["supertrend"] = Indicators.supertrend(df["high"], df["low"], df["close"], p["period"], p["multiplier"])
        elif e_type == "mean_rev_bb":
            p = e_conf[e_type]
            u, m, l = Indicators.bollinger_bands(df["close"], p["period"], p["std"])
            df["bb_upper"] = u
            df["bb_lower"] = l
        elif e_type == "breakout_donchian":
            p = e_conf[e_type]
            u, l = Indicators.donchian(df["high"], df["low"], p["period"])
            df["dc_upper"] = u
            df["dc_lower"] = l

        # Filters
        for f in self.strategy.get("filters", []):
            ft = f["type"]
            p = f["params"]
            if ft == "adx_filter":
                df["adx"] = Indicators.adx(df["high"], df["low"], df["close"], p["period"])
            elif ft == "ema_filter_long":
                df["ema_long"] = Indicators.ema(df["close"], p["period"])

    def _generate_signals(self, df):
        # 1 = Buy, -1 = Sell, 0 = Flat/Hold
        signals = pd.Series(0, index=df.index)

        e_conf = self.strategy.get("entry", {})
        e_type = next(iter(e_conf)) if e_conf else None

        if e_type == "trend_ema_cross":
            # Crossover logic
            # Long: fast crosses above slow
            # Short: fast crosses below slow (if short enabled, let's assume long only for now as per spec default)
            # Actually spec says "Long-only default; short optional". Let's stick to Long Only.

            # Using shift to detect crossover
            prev_fast = df["ema_fast"].shift(1)
            prev_slow = df["ema_slow"].shift(1)
            curr_fast = df["ema_fast"]
            curr_slow = df["ema_slow"]

            long_cond = (prev_fast <= prev_slow) & (curr_fast > curr_slow)
            signals[long_cond] = 1

        elif e_type == "trend_supertrend":
            # Long when close > supertrend (uptrend)
            # But we want the FLIP to uptrend as entry
            # Supertrend indicator returns the line, we need to infer direction or compute it.
            # In our adapter, we only returned the line. Let's infer:
            # If close > supertrend, it's support (uptrend). If close < supertrend, it's resistance (downtrend).

            is_uptrend = df["close"] > df["supertrend"]
            long_cond = (is_uptrend) & (~is_uptrend.shift(1).fillna(False))
            signals[long_cond] = 1

        elif e_type == "mean_rev_rsi":
            p = e_conf[e_type]
            # Long when RSI < lower
            long_cond = df["rsi"] < p["lower"]
            signals[long_cond] = 1

        elif e_type == "mean_rev_bb":
            # Long when close < lower band
            long_cond = df["close"] < df["bb_lower"]
            signals[long_cond] = 1

        elif e_type == "breakout_donchian":
            # Long when close > dc_upper (previous bar's upper?)
            # Usually donchian is high(n). Breakout is close > high(n).
            # Our adapter returns rolling max of high.
            # Careful: rolling max includes current high if window is aligned.
            # Proper breakout: close > max(high of prev n bars).
            # The adapter computes `rolling(window).max()`.
            # We should compare close to `dc_upper.shift(1)`
            long_cond = df["close"] > df["dc_upper"].shift(1)
            signals[long_cond] = 1

        # Apply Filters
        for f in self.strategy.get("filters", []):
            ft = f["type"]
            p = f["params"]
            if ft == "adx_filter":
                # Only trade if ADX > threshold
                mask = df["adx"] > p["threshold"]
                signals = signals & mask
            elif ft == "ema_filter_long":
                # Only trade if Close > EMA long
                mask = df["close"] > df["ema_long"]
                signals = signals & mask

        return signals

    def _simulate_execution(self, df, signals):
        trades = []
        position = 0 # 0, 1
        entry_price = 0.0
        entry_idx = 0
        entry_time = None

        exit_conf = self.strategy.get("exit", {})

        # params
        stop_atr = exit_conf.get("atr_stop")
        stop_time = exit_conf.get("time_stop")
        take_profit = exit_conf.get("fixed_tp")

        # Pre-calc ATR if needed for stops
        atr_series = df["atr"] if "atr" in df.columns else pd.Series(0, index=df.index)

        # Iterate bars
        # Note: Vectorized backtesting is faster, but event-driven loop is needed for complex exits (trailing, time, intraday flatten)
        # We will use a simple loop over the dataframe for correctness with path-dependent exits.

        flatten_time = MarketHours.get_flatten_time()

        for i in range(len(df)):
            if i == 0: continue

            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            ts = bar["timestamp"]

            # Check for Exits if in position
            if position > 0:
                exit_reason = None
                exit_price = 0.0

                # 1. Intraday Flatten
                # If timestamp time >= 15:25
                if ts.time() >= flatten_time:
                    exit_reason = "EOD"
                    exit_price = bar["close"] # Assuming we close at close of this bar (or open of next, but for EOD we force close)

                # 2. Time Stop
                elif stop_time and (i - entry_idx) >= stop_time["bars"]:
                    exit_reason = "Time"
                    exit_price = bar["open"]

                # 3. ATR Stop / Fixed SL
                # Check low of current bar against SL
                # SL calculated at entry
                elif stop_atr:
                    # We need the ATR at entry
                    # Simplification: Calculate SL once at entry
                    pass

                # 4. TP
                # Check high of current bar

                # Execute Exit
                if exit_reason:
                    pnl = (exit_price - entry_price) / entry_price
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": pnl,
                        "reason": exit_reason,
                        "bars_held": i - entry_idx
                    })
                    position = 0
                    continue

            # Check for Entry if flat
            # Signal is generated based on data available at i (close of i).
            # We enter at Open of i+1.
            # So if signals[i] == 1, we set flag to enter next bar.

            # Actually, let's look at `signals` computed previously.
            # `signals[i]` uses `df.iloc[i]` data.
            # If `signals[i-1] == 1` and we are flat, we enter at `bar["open"]`.

            if position == 0:
                sig = signals.iloc[i-1]
                if sig == 1:
                    # Check not EOD
                    if ts.time() < flatten_time:
                        position = 1
                        entry_price = bar["open"]
                        entry_idx = i
                        entry_time = ts

                        # Set SL/TP levels
                        current_atr = atr_series.iloc[i-1]

                        # Store in local vars for the loop
                        self.sl_price = entry_price - (current_atr * stop_atr["multiple"]) if stop_atr else -99999
                        self.tp_price = entry_price + (current_atr * take_profit["multiple_of_risk"]) if take_profit else 99999

            # In-bar SL/TP check (if position was just opened or already open)
            if position > 0:
                # Check Low against SL
                if bar["low"] <= self.sl_price:
                     exit_price = self.sl_price # Assume slippage handled in costs later
                     # Or exit at Close if gap down? Conservative: min(Open, SL) but simplest is SL level.
                     # Let's use SL level but capped at Open if Open < SL (gap down)
                     if bar["open"] < self.sl_price:
                         exit_price = bar["open"]

                     trades.append({
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": (exit_price - entry_price) / entry_price,
                        "reason": "SL",
                        "bars_held": i - entry_idx
                    })
                     position = 0
                     continue

                # Check High against TP
                if bar["high"] >= self.tp_price:
                     exit_price = self.tp_price
                     if bar["open"] > self.tp_price:
                         exit_price = bar["open"]

                     trades.append({
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": (exit_price - entry_price) / entry_price,
                        "reason": "TP",
                        "bars_held": i - entry_idx
                    })
                     position = 0
                     continue

        return pd.DataFrame(trades)

    def _compute_metrics(self, trades_df, df):
        if trades_df.empty:
            return {"sharpe": -99, "cagr": 0, "max_dd": 0, "trades": 0, "win_rate": 0, "profit_factor": 0}

        # Apply costs
        total_cost_bps = self.costs["all_in_cost_bps_per_side"] + self.costs["slippage_bps_per_side"]
        trades_df["net_pnl"] = trades_df["pnl_pct"] - (2 * total_cost_bps / 10000)

        # Equity Curve
        trades_df["equity"] = (1 + trades_df["net_pnl"]).cumprod()

        # Metrics
        n_trades = len(trades_df)
        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] <= 0]

        win_rate = len(wins) / n_trades
        avg_win = wins["net_pnl"].mean() if not wins.empty else 0
        avg_loss = abs(losses["net_pnl"].mean()) if not losses.empty else 0
        profit_factor = (wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty and losses["net_pnl"].sum() != 0 else 0

        # Sharpe
        # Resample to daily for annualized metrics or use trade based?
        # Standard: annualized from trade returns is tricky.
        # Better: Reconstruct daily equity curve from trades + underlying index for time-weighted.
        # Approximation: Sharpe of trade returns * sqrt(trades per year)

        days_in_data = (df["timestamp"].max() - df["timestamp"].min()).days
        if days_in_data < 1: days_in_data = 1
        trades_per_year = n_trades / (days_in_data / 365.25)

        avg_ret = trades_df["net_pnl"].mean()
        std_ret = trades_df["net_pnl"].std()

        sharpe = (avg_ret / std_ret * np.sqrt(trades_per_year)) if std_ret > 0 else 0

        # Max DD
        eq = trades_df["equity"]
        peak = eq.cummax()
        dd = (eq - peak) / peak
        max_dd = dd.min()

        # Calmar
        cagr = (eq.iloc[-1]) ** (365.25 / days_in_data) - 1
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        return {
            "sharpe": sharpe,
            "cagr": cagr,
            "max_dd": abs(max_dd),
            "calmar": calmar,
            "trades": n_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "equity_curve": eq.tolist() if not eq.empty else []
        }

if __name__ == "__main__":
    # Test stub
    pass
