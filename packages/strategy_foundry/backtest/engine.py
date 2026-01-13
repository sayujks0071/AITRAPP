"""Backtest Engine for Intraday Strategies"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate, EntryType, FilterType, ExitType
from packages.strategy_foundry.adapters.core_indicators import IndicatorCalculator

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, costs_bps=5.0):
        self.data = data.copy()
        self.costs_bps = costs_bps
        self.calculator = IndicatorCalculator()

    def _prepare_indicators(self, candidate: StrategyCandidate):
        df = self.data.copy()

        # Helper for EMA
        def ema(series, span):
            return series.ewm(span=span, adjust=False).mean()

        # Helper for ATR
        def atr(high, low, close, period):
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(period).mean()

        # Helper for RSI
        def rsi(close, period):
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        # Entry logic preparation
        e = candidate.entry_block
        p = e["params"]
        if e["type"] == EntryType.EMA_CROSS:
            df[f"ema_{p['fast']}"] = ema(df["close"], p["fast"])
            df[f"ema_{p['slow']}"] = ema(df["close"], p["slow"])
        elif e["type"] == EntryType.RSI_OVERSOLD:
            df["rsi"] = rsi(df["close"], p["period"])
        elif e["type"] == EntryType.SUPERTREND:
            pass
        elif e["type"] == EntryType.DONCHIAN_BREAKOUT:
            df["donchian_high"] = df["high"].rolling(p["period"]).max().shift(1)
            df["donchian_low"] = df["low"].rolling(p["period"]).min().shift(1)

        # Exits preparation
        for x in candidate.exit_blocks:
            if x["type"] == ExitType.STOP_LOSS_ATR:
                df["atr"] = atr(df["high"], df["low"], df["close"], x["params"]["period"])

        # Filters preparation
        for f in candidate.filter_blocks:
            if f["type"] == FilterType.REGIME_SMA:
                df["regime_sma"] = df["close"].rolling(f["params"]["period"]).mean()

        return df

    def run(self, candidate: StrategyCandidate) -> Dict[str, Any]:
        df = self._prepare_indicators(candidate)

        # State
        position = 0 # 1 or 0 (long only)
        entry_price = 0.0
        trades = []
        equity = [100.0]

        # 1. Entry Signals
        entry_signal = pd.Series(False, index=df.index)

        e = candidate.entry_block
        p = e["params"]

        if e["type"] == EntryType.EMA_CROSS:
            fast = df[f"ema_{p['fast']}"]
            slow = df[f"ema_{p['slow']}"]
            entry_signal = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        elif e["type"] == EntryType.RSI_OVERSOLD:
            entry_signal = (df["rsi"] < p["threshold"])
        elif e["type"] == EntryType.DONCHIAN_BREAKOUT:
            entry_signal = (df["close"] > df["donchian_high"])

        # Apply filters
        for f in candidate.filter_blocks:
            if f["type"] == FilterType.REGIME_SMA:
                mask = df["close"] > df["regime_sma"]
                entry_signal = entry_signal & mask

        # 2. Iteration for Exits
        dates = df.index
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        entry_sigs = entry_signal.values

        atr_vals = df["atr"].values if "atr" in df.columns else np.zeros(len(df))

        # Exit params
        atr_stop_mult = 0
        for x in candidate.exit_blocks:
            if x["type"] == ExitType.STOP_LOSS_ATR:
                atr_stop_mult = x["params"]["mult"]

        current_stop = 0.0
        entry_idx = 0

        session_end_strs = [x["params"]["time"] for x in candidate.exit_blocks if x["type"] == ExitType.SESSION_CLOSE]
        session_end_hm = int(session_end_strs[0].replace(":", "")) if session_end_strs else 1525

        for i in range(1, len(df)):
            date = dates[i]
            # Market check: 15:25
            curr_hm = date.hour * 100 + date.minute
            is_session_end = curr_hm >= session_end_hm

            # Check Exit
            if position == 1:
                exit_price = 0.0
                reason = ""

                # SL Check (Low penetrates stop)
                if lows[i] < current_stop:
                    exit_price = current_stop
                    if opens[i] < current_stop:
                        exit_price = opens[i]
                    reason = "SL"
                # Session Close
                elif is_session_end:
                    exit_price = closes[i]
                    reason = "Session"

                if exit_price > 0:
                    # Execute Exit
                    pnl_pct = (exit_price - entry_price) / entry_price
                    # Costs
                    cost_pct = (self.costs_bps * 2) / 10000.0
                    net_pnl = pnl_pct - cost_pct

                    trades.append({
                        "entry_time": dates[entry_idx],
                        "exit_time": date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_net": net_pnl,
                        "reason": reason
                    })
                    position = 0
                    equity.append(equity[-1] * (1 + net_pnl))
                    continue # Next bar

            # Check Entry (if flat and not session end)
            if position == 0 and not is_session_end:
                if entry_sigs[i-1]: # Signal on CLOSE of prev bar -> Enter OPEN of current
                    position = 1
                    entry_price = opens[i]
                    entry_idx = i

                    # Set Initial Stop
                    if atr_stop_mult > 0:
                        vol = atr_vals[i-1]
                        if np.isnan(vol): vol = entry_price * 0.01
                        current_stop = entry_price - (vol * atr_stop_mult)
                    else:
                        current_stop = entry_price * 0.99

        # Stats
        df_trades = pd.DataFrame(trades)
        final_equity = equity[-1]

        if not df_trades.empty:
            win_rate = len(df_trades[df_trades["pnl_net"] > 0]) / len(df_trades)
            avg_ret = df_trades["pnl_net"].mean()

            # Determine annualized factor based on data freq
            # Assume 15m (25 bars/day), 5m (75 bars/day), 1D (1 bar/day)
            # Default to 5m logic (75*252) if unknown, but better to detect
            freq_mins = pd.Timedelta(dates[1] - dates[0]).seconds / 60
            if freq_mins > 1400: # Daily
                bars_per_year = 252
            elif freq_mins > 10: # 15m (approx)
                bars_per_year = 25 * 252
            else: # 5m or less
                bars_per_year = 75 * 252

            # Calculate Sharpe correctly using per-trade returns is WRONG usually.
            # We should construct a daily equity curve and calculate Daily Sharpe.
            # But constructing daily curve from trade list is complex in this lightweight engine.
            # Approximation: sqrt(TradesPerYear) * (MeanTrade / StdTrade)
            # TradesPerYear = TotalTrades / (TotalDays / 252)
            total_days = (dates[-1] - dates[0]).days
            if total_days < 1: total_days = 1
            trades_per_year = len(df_trades) * (365 / total_days) # Calendar days approx

            std_ret = df_trades["pnl_net"].std()
            if std_ret > 0:
                sharpe = (avg_ret / std_ret) * np.sqrt(trades_per_year)
            else:
                sharpe = 0

            # Max DD
            eq_arr = np.array(equity)
            peaks = np.maximum.accumulate(eq_arr)
            dds = (peaks - eq_arr) / peaks
            max_dd = np.max(dds)

            cum_ret = (final_equity - 100.0)/100.0

            # Profit Factor
            gross_win = df_trades[df_trades["pnl_net"] > 0]["pnl_net"].sum()
            gross_loss = abs(df_trades[df_trades["pnl_net"] <= 0]["pnl_net"].sum())
            profit_factor = gross_win / gross_loss if gross_loss > 0 else 99.0

        else:
            win_rate = 0.0
            avg_ret = 0.0
            sharpe = 0.0
            max_dd = 0.0
            cum_ret = 0.0
            profit_factor = 0.0

        return {
            "candidate_id": candidate.id,
            "total_trades": len(df_trades),
            "trades": len(df_trades),
            "win_rate": win_rate,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "profit_factor": profit_factor,
            "total_return": cum_ret,
            "equity_curve": equity
        }
