from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter
from packages.strategy_foundry.adapters.core_costs import CostAdapter
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class BacktestEngine:
    """
    Daily Backtest Engine.
    Executes signals at Next Open.
    """
    def __init__(self, slippage_bps=5.0, all_in_cost_bps=10.0):
        self.costs = CostAdapter(slippage_bps, all_in_cost_bps)
        self.indicators = IndicatorsAdapter()

    def run(self, df: pd.DataFrame, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run backtest.

        Args:
            df: OHLCV DataFrame
            spec: Strategy specification (dict)

        Returns:
            Dict with metrics, trades, equity curve.
        """
        if df.empty:
            return {}

        # 1. Prepare Indicators
        data = df.copy()
        self._prepare_indicators(data, spec)

        # 2. Generate Signals
        self._generate_signals(data, spec)

        # 3. Simulate Execution
        trades, equity_curve, final_pos = self._simulate(data, spec)

        # 4. Calculate Metrics
        trades_df = pd.DataFrame(trades)
        daily_equity = equity_curve # Already daily
        daily_returns = daily_equity.pct_change().fillna(0)

        metrics = calculate_metrics(trades_df, daily_returns)

        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "final_position": final_pos
        }

    def _prepare_indicators(self, df: pd.DataFrame, spec: Dict[str, Any]):
        # This will be delegated to the Strategy Factory/Grammar usually,
        # but for now we implement the interpretation here.
        # Actually, the grammar should probably produce "signals" or the engine should use the grammar to compute them.
        # The prompt says: "Unified interface every strategy must implement ... generate_positions(df)".
        # BUT the prompt also says "Implement strategy grammar...".
        # If I strictly follow the prompt "Unified interface", the `spec` should be an object that has `generate_positions`.
        # However, to keep it serializable (JSON), `spec` is likely a dict, and we interpret it.

        # I'll implement a simple interpreter for the components described in the prompt.
        # "Trend: EMA/SMA cross...", "Mean reversion: RSI...", "Filters..."

        # To avoid massive if-else here, I'll rely on the `spec` having parameters that `IndicatorsAdapter` can use.
        # I'll compute common indicators lazily or based on keys.

        # Assuming spec has "components" list or similar.
        # For simplicity, let's assume spec structure:
        # {
        #   "type": "EMA_CROSS",
        #   "params": { "fast": 20, "slow": 50 },
        #   "filter": { "type": "RSI", "params": {"period": 14, "threshold": 30} },
        #   "stop": { "type": "ATR", "params": {"period": 14, "mult": 2.0} }
        # }

        pass # Indicators calculated on fly or in generate_signals

    def _generate_signals(self, df: pd.DataFrame, spec: Dict[str, Any]):
        # Initialize
        df["signal"] = 0 # 1 (Long), -1 (Short), 0 (Flat)

        # Interpreter
        st_type = spec.get("type")
        params = spec.get("params", {})

        entry_long = pd.Series(False, index=df.index)
        exit_long = pd.Series(False, index=df.index) # Logic exit

        # --- Entry Logic ---
        if st_type == "EMA_CROSS":
            fast = self.indicators.ema(df["close"], params.get("fast", 20))
            slow = self.indicators.ema(df["close"], params.get("slow", 50))
            # Cross over
            entry_long = (fast > slow) & (fast.shift(1) <= slow.shift(1))
            exit_long = (fast < slow)

        elif st_type == "RSI_REVERSION":
            rsi = self.indicators.rsi(df, params.get("period", 14))
            entry_long = rsi < params.get("lower", 30)
            exit_long = rsi > params.get("upper", 70)

        elif st_type == "DONCHIAN_BREAKOUT":
            upper, lower, _ = self.indicators.donchian(df, params.get("period", 20))
            # Breakout: Close > prev upper
            entry_long = df["close"] > upper.shift(1)
            exit_long = df["close"] < lower.shift(1) # Stop and reverse or just exit?

        elif st_type == "SUPERTREND":
            st, direction = self.indicators.supertrend(df, params.get("period", 10), params.get("multiplier", 3.0))
            entry_long = (direction == 1) & (direction.shift(1) == -1)
            exit_long = (direction == -1)

        # --- Filters ---
        filter_spec = spec.get("filter")
        if filter_spec:
            f_type = filter_spec.get("type")
            f_params = filter_spec.get("params", {})

            if f_type == "RSI":
                rsi = self.indicators.rsi(df, f_params.get("period", 14))
                if f_params.get("mode") == "below":
                    entry_long = entry_long & (rsi < f_params.get("threshold", 70))
                else:
                    entry_long = entry_long & (rsi > f_params.get("threshold", 30))
            elif f_type == "ADX":
                adx = self.indicators.adx(df, f_params.get("period", 14))
                entry_long = entry_long & (adx > f_params.get("threshold", 25))
            elif f_type == "REGIME_SMA":
                sma = self.indicators.sma(df["close"], f_params.get("period", 200))
                entry_long = entry_long & (df["close"] > sma)

        df["entry_long"] = entry_long
        df["exit_logic"] = exit_long

        # Calculate ATR for Stops if needed
        stop_spec = spec.get("stop")
        if stop_spec and stop_spec.get("type") == "ATR":
             df["atr"] = self.indicators.atr(df, stop_spec.get("params", {}).get("period", 14))

    def _simulate(self, df: pd.DataFrame, spec: Dict[str, Any]) -> Tuple[List, pd.Series, int]:
        """
        Simulate trades (Long Only for now as per default).
        Execution: Signal at Close[i] -> Trade at Open[i+1].
        """
        trades = []
        equity = 100000.0
        equity_curve = []

        position = 0 # 0, 1
        entry_price = 0.0
        entry_idx = None
        sl_price = 0.0
        tp_price = 0.0
        bars_held = 0

        stop_spec = spec.get("stop", {})
        stop_type = stop_spec.get("type", "NONE")
        stop_params = stop_spec.get("params", {})

        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        entries = df["entry_long"].values
        exits_logic = df["exit_logic"].values
        atrs = df["atr"].values if "atr" in df.columns else np.zeros(len(df))

        timestamps = df.index

        n = len(df)

        total_cost_bps = self.costs.estimate_total_cost_bps()
        cost_pct = total_cost_bps / 10000.0

        for i in range(n - 1): # Can't trade on last bar for next open
            # Mark to market
            current_equity = equity
            if position == 1:
                # Unrealized PnL based on Close
                change = (closes[i] - entry_price) / entry_price
                current_equity = equity * (1 + change)

            equity_curve.append(current_equity)

            # 1. Manage Open Position
            if position == 1:
                bars_held += 1
                exit_price = None
                reason = ""

                # Check Logic Exit (Signal at Close[i] -> Exit Open[i+1])
                # Check Stops (Hit Intra-day [i] or Gap [i])
                # Actually, if we execute at Open[i+1], we check stops on Bar[i+1]?
                # No, we held through Bar[i].
                # If we entered at Open[i], we check stops on Bar[i].
                # Wait, loop index i represents "Today".
                # If I entered at Open[i] (decided at i-1), I check stops on Bar[i].
                # My loop structure: "i" is "Today".
                # If position=1, it means I am ALREADY holding at start of "Today".

                # Check SL/TP on Today's OHLC
                # Assumes SL/TP orders are active during the day

                sl_hit = (lows[i] <= sl_price)
                tp_hit = (highs[i] >= tp_price) if tp_price > 0 else False

                if sl_hit:
                    exit_price = min(opens[i], sl_price) # Gap handling: if open < sl, we exit at open
                    reason = "SL"
                elif tp_hit:
                    exit_price = max(opens[i], tp_price) # Gap handling
                    reason = "TP"
                elif exits_logic[i]:
                    # Logic signal at Close[i] -> Exit Open[i+1]
                    # We will exit tomorrow Open. Mark for exit.
                    pass
                elif stop_type == "TIME" and bars_held >= stop_params.get("max_bars", 10):
                    # Time stop: Exit Open[i+1]
                    pass
                elif stop_type == "TRAILING_ATR":
                     # Update SL
                     new_sl = closes[i] - (atrs[i] * stop_params.get("mult", 3.0))
                     if new_sl > sl_price:
                         sl_price = new_sl

                if exit_price is not None:
                    # Executed TODAY
                    # PnL
                    ret = (exit_price - entry_price) / entry_price
                    ret_net = ret - cost_pct
                    pnl = equity * ret_net
                    equity += pnl
                    position = 0
                    trades.append({
                        "entry_time": timestamps[entry_idx],
                        "exit_time": timestamps[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "return_pct": ret_net,
                        "reason": reason
                    })
                    continue # Done for this bar

                # Check if we need to exit Next Open due to Logic or Time
                exit_next_open = False
                exit_reason_next = ""

                if exits_logic[i]:
                    exit_next_open = True
                    exit_reason_next = "SIGNAL"
                elif stop_type == "TIME" and bars_held >= stop_params.get("max_bars", 10):
                    exit_next_open = True
                    exit_reason_next = "TIME"

                if exit_next_open:
                    exit_price = opens[i+1]
                    ret = (exit_price - entry_price) / entry_price
                    ret_net = ret - cost_pct
                    pnl = equity * ret_net
                    equity += pnl
                    position = 0
                    trades.append({
                        "entry_time": timestamps[entry_idx],
                        "exit_time": timestamps[i+1],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "return_pct": ret_net,
                        "reason": exit_reason_next
                    })
                    continue

            # 2. Check Entry (if flat)
            if position == 0:
                if entries[i]:
                    # Signal at Close[i] -> Enter Open[i+1]
                    entry_price = opens[i+1]
                    entry_idx = i+1
                    position = 1
                    bars_held = 0

                    # Set Initial Stops based on Bar[i] (Signal Bar)
                    if stop_type == "ATR":
                        atr_val = atrs[i]
                        sl_price = entry_price - (atr_val * stop_params.get("sl_mult", 2.0))
                        if "tp_mult" in stop_params:
                            tp_price = entry_price + (atr_val * stop_params.get("tp_mult"))
                        else:
                            tp_price = 0.0 # No TP
                    elif stop_type == "TRAILING_ATR":
                         atr_val = atrs[i]
                         sl_price = entry_price - (atr_val * stop_params.get("mult", 3.0))
                         tp_price = 0.0
                    else:
                        sl_price = 0.0 # No SL
                        tp_price = 0.0

        # Last bar equity
        equity_curve.append(equity)

        # Series
        equity_series = pd.Series(equity_curve, index=timestamps[:len(equity_curve)])

        return trades, equity_series, position
