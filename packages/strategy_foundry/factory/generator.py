from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_indicators import FoundryIndicators

logger = structlog.get_logger(__name__)

class GeneratedStrategy:
    """
    Concrete implementation of a generated strategy.
    Takes a candidate definition and provides `generate_positions` method.
    """

    def __init__(self, candidate: StrategyCandidate):
        self.candidate = candidate
        self.grammar = candidate.grammar
        self.params = candidate.params

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generates target positions (-1, 0, 1) for the given dataframe.
        Vectorized where possible.
        """
        # 1. Indicators
        indicators = self._calc_indicators(df)

        # 2. Raw Signals
        long_signal, short_signal = self._calc_entry_signals(df, indicators)

        # 3. Filters
        mask = self._calc_filters(df, indicators)
        long_signal = long_signal & mask
        short_signal = short_signal & mask

        # 4. Exits / State Machine
        # Since vectorizing stateful exits (trailing stop, RR) is hard without loop,
        # we will use a Numba-friendly or simple iterative approach for the state machine.
        # For simplicity and robustness in this version, we use a simple loop over numpy arrays.

        positions = self._apply_risk_and_exits(df, indicators, long_signal, short_signal)

        return pd.Series(positions, index=df.index)

    def _calc_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        ind = {}
        # Always calc ATR for normalization
        ind["atr"] = FoundryIndicators.atr(df, period=14).values

        p = self.params

        # Entry Indicators
        if self.grammar["entry_type"] == "EMA_CROSS":
            ind["ema_fast"] = FoundryIndicators.ema(df["close"], p["ema_fast"]).values
            ind["ema_slow"] = FoundryIndicators.ema(df["close"], p["ema_slow"]).values

        elif self.grammar["entry_type"] == "SUPERTREND_FLIP":
            st, direction = FoundryIndicators.supertrend(df, p["st_period"], p["st_multiplier"])
            ind["st_val"] = st.values
            ind["st_dir"] = direction.values

        elif self.grammar["entry_type"] == "RSI_REVERSION":
            ind["rsi"] = FoundryIndicators.rsi(df["close"], p["rsi_period"]).values

        elif self.grammar["entry_type"] == "BB_REVERSION":
            u, m, l = FoundryIndicators.bollinger_bands(df["close"], p["bb_period"], p["bb_std"])
            ind["bb_lower"] = l.values
            ind["bb_upper"] = u.values

        elif self.grammar["entry_type"] == "DONCHIAN_BREAKOUT":
            u, l = FoundryIndicators.donchian(df, p["donchian_period"])
            ind["dc_upper"] = u.values
            ind["dc_lower"] = l.values

        # Filter Indicators
        if self.grammar["filter_type"] == "ADX_FILTER":
            ind["adx"] = FoundryIndicators.adx(df, p["adx_period"]).values
        elif self.grammar["filter_type"] == "SMA_REGIME":
            ind["regime_sma"] = FoundryIndicators.sma(df["close"], p["regime_sma"]).values
        elif self.grammar["filter_type"] == "RSI_FILTER":
            if "rsi" not in ind:
                ind["rsi"] = FoundryIndicators.rsi(df["close"], p["rsi_filter_period"]).values

        return ind

    def _calc_entry_signals(self, df: pd.DataFrame, ind: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        n = len(df)
        longs = np.zeros(n, dtype=bool)
        shorts = np.zeros(n, dtype=bool)
        close = df["close"].values
        p = self.params

        if self.grammar["entry_type"] == "EMA_CROSS":
            # Crossover: Fast > Slow today AND Fast < Slow yesterday
            # We use shift logic: (Fast > Slow) & (Fast.shift(1) <= Slow.shift(1))
            fast = ind["ema_fast"]
            slow = ind["ema_slow"]
            longs = (fast > slow) & (np.roll(fast, 1) <= np.roll(slow, 1))
            shorts = (fast < slow) & (np.roll(fast, 1) >= np.roll(slow, 1))

        elif self.grammar["entry_type"] == "SUPERTREND_FLIP":
            # Flip from -1 to 1 (Long) or 1 to -1 (Short)
            d = ind["st_dir"]
            prev_d = np.roll(d, 1)
            longs = (d == 1) & (prev_d == -1)
            shorts = (d == -1) & (prev_d == 1)

        elif self.grammar["entry_type"] == "RSI_REVERSION":
            # Long: RSI crosses below lower (oversold) -> Expect bounce?
            # Usually reversion means buy when it crosses back UP from oversold
            # Let's say: Buy when RSI < Lower
            rsi = ind["rsi"]
            longs = rsi < p["rsi_lower"]
            shorts = rsi > p["rsi_upper"]

        elif self.grammar["entry_type"] == "BB_REVERSION":
            # Buy when Close < Lower
            longs = close < ind["bb_lower"]
            shorts = close > ind["bb_upper"]

        elif self.grammar["entry_type"] == "DONCHIAN_BREAKOUT":
            # Buy when Close > Upper
            longs = close > np.roll(ind["dc_upper"], 1) # Breakout of YESTERDAY'S high
            shorts = close < np.roll(ind["dc_lower"], 1)

        # Default: First element always false (due to shift/roll)
        longs[0] = False
        shorts[0] = False

        return longs, shorts

    def _calc_filters(self, df: pd.DataFrame, ind: Dict[str, Any]) -> np.ndarray:
        n = len(df)
        mask = np.ones(n, dtype=bool)
        p = self.params
        close = df["close"].values

        if self.grammar["filter_type"] == "ADX_FILTER":
            # Trend filter: ADX > Threshold
            mask = ind["adx"] > p["adx_threshold"]

        elif self.grammar["filter_type"] == "SMA_REGIME":
            # Bullish only if price > 200 SMA
            mask = close > ind["regime_sma"]

        elif self.grammar["filter_type"] == "RSI_FILTER":
            # Bullish only if RSI > 50
            mask = ind["rsi"] > 50

        return mask

    def _apply_risk_and_exits(self, df: pd.DataFrame, ind: Dict[str, Any],
                              long_signals: np.ndarray, short_signals: np.ndarray) -> np.ndarray:
        """
        Iterates through bars to manage position state (entry, stop, exit).
        Returns array of positions: 1 (long), -1 (short), 0 (flat).
        """
        n = len(df)
        positions = np.zeros(n, dtype=int)

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        dates = df.index

        # State
        current_pos = 0 # 0, 1, -1
        entry_price = 0.0
        stop_price = 0.0
        bars_held = 0

        p = self.params

        for i in range(1, n): # Start from 1 to lookback
            # 1. Update existing position (Check exits)
            if current_pos != 0:
                bars_held += 1
                exit_signal = False

                # Update trailing stop if applicable
                if self.grammar["stop_type"] == "ATR_STOP":
                    atr_val = ind["atr"][i-1]
                    if current_pos == 1:
                        new_stop = close[i] - (atr_val * p["stop_atr_mult"])
                        stop_price = max(stop_price, new_stop) # Trailing up
                    else:
                        new_stop = close[i] + (atr_val * p["stop_atr_mult"])
                        stop_price = min(stop_price, new_stop) # Trailing down

                # Check Stop Loss Hit
                if current_pos == 1 and low[i] < stop_price:
                    current_pos = 0
                    exit_signal = True
                elif current_pos == -1 and high[i] > stop_price:
                    current_pos = 0
                    exit_signal = True

                # Check Target / other exits
                if not exit_signal:
                    if self.grammar["exit_type"] == "FIXED_RR":
                        risk = abs(entry_price - stop_price)
                        target = entry_price + (risk * p["rr_ratio"] * current_pos)
                        if (current_pos == 1 and high[i] >= target) or \
                           (current_pos == -1 and low[i] <= target):
                            current_pos = 0

                    elif self.grammar["exit_type"] == "TIME_EXIT":
                        if bars_held >= p["max_bars"]:
                            current_pos = 0

                    elif self.grammar["exit_type"] == "INDICATOR_EXIT":
                        # Reverse signal exit
                        if (current_pos == 1 and short_signals[i]) or \
                           (current_pos == -1 and long_signals[i]):
                            current_pos = 0

            # 2. Check Entries (if flat)
            if current_pos == 0:
                if long_signals[i]:
                    current_pos = 1
                    entry_price = close[i]
                    bars_held = 0
                    # Set Initial Stop
                    if self.grammar["stop_type"] == "ATR_STOP":
                        stop_price = close[i] - (ind["atr"][i] * p["stop_atr_mult"])
                    elif self.grammar["stop_type"] == "PCT_STOP":
                        stop_price = close[i] * (1 - p["stop_pct"])
                    elif self.grammar["stop_type"] == "LOW_HIGH_STOP":
                        lookback = p["stop_lookback"]
                        stop_price = np.min(low[max(0, i-lookback):i])
                    else:
                         stop_price = close[i] * 0.95 # Fallback

                # Only Longs supported by default in most simple strategies,
                # but let's allow shorts if signaled.
                # (User prompt said "Long-only by default (short allowed only if config enables)")
                # For now we implement logic, but we can filter shorts later or via config.
                elif short_signals[i]:
                    current_pos = -1
                    entry_price = close[i]
                    bars_held = 0
                    if self.grammar["stop_type"] == "ATR_STOP":
                        stop_price = close[i] + (ind["atr"][i] * p["stop_atr_mult"])
                    elif self.grammar["stop_type"] == "PCT_STOP":
                        stop_price = close[i] * (1 + p["stop_pct"])
                    elif self.grammar["stop_type"] == "LOW_HIGH_STOP":
                        lookback = p["stop_lookback"]
                        stop_price = np.max(high[max(0, i-lookback):i])
                    else:
                        stop_price = close[i] * 1.05

            positions[i] = current_pos

        return positions
