"""Technical indicator calculations"""
from typing import Dict, Optional

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class IndicatorCalculator:
    """Calculates technical indicators from OHLCV data"""

    def __init__(
        self,
        atr_period: int = 14,
        rsi_period: int = 14,
        adx_period: int = 14,
        ema_fast: int = 34,
        ema_slow: int = 89,
        supertrend_period: int = 10,
        supertrend_multiplier: float = 3.0,
        bb_period: int = 20,
        bb_std: float = 2.0
    ):
        self.atr_period = atr_period
        self.rsi_period = rsi_period
        self.adx_period = adx_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.supertrend_period = supertrend_period
        self.supertrend_multiplier = supertrend_multiplier
        self.bb_period = bb_period
        self.bb_std = bb_std

    def _rolling_mean(self, arr: np.ndarray, window: int) -> np.ndarray:
        """
        Fast rolling mean using NumPy convolution.
        Matches pandas rolling(window).mean() behavior (propagates NaNs).

        Args:
            arr: Input numpy array (1D)
            window: Rolling window size

        Returns:
            Numpy array of same size as input, with NaN padding at start.
        """
        n = len(arr)
        if n < window:
             return np.full(n, np.nan)

        kernel = np.ones(window) / window
        # mode='valid' returns size N - W + 1
        result = np.convolve(arr, kernel, mode='valid')

        # Pad with NaNs at the beginning to match size and pandas alignment
        pad = np.full(window - 1, np.nan)
        return np.concatenate((pad, result))

    def compute_all(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Compute all indicators and return latest values.

        Args:
            df: DataFrame with columns: open, high, low, close, volume

        Returns:
            Dict of indicator names to values
        """
        if df.empty or len(df) < max(self.atr_period, self.rsi_period, self.adx_period, self.ema_slow):
            return {}

        try:
            indicators = {}

            # Pre-calculate TR once (used by ATR, ADX, Supertrend)
            # This avoids redundant expensive calculations (3x speedup for TR)
            tr = self._calculate_tr(df)

            # VWAP (reset daily in production)
            indicators["vwap"] = self._vwap(df)

            # ATR (reuse TR)
            indicators["atr"] = self._atr(df, tr=tr)

            # RSI
            indicators["rsi"] = self._rsi(df)

            # ADX (reuse TR)
            indicators["adx"] = self._adx(df, tr=tr)

            # EMAs
            indicators["ema_fast"] = self._ema(df["close"], self.ema_fast)
            indicators["ema_slow"] = self._ema(df["close"], self.ema_slow)

            # Supertrend (reuse TR)
            st_val, st_dir = self._supertrend(df, tr=tr)
            indicators["supertrend"] = st_val
            indicators["supertrend_direction"] = st_dir

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._bollinger_bands(df["close"])
            indicators["bb_upper"] = bb_upper
            indicators["bb_middle"] = bb_middle
            indicators["bb_lower"] = bb_lower

            # Donchian Channel
            dc_upper, dc_lower = self._donchian(df)
            indicators["dc_upper"] = dc_upper
            indicators["dc_lower"] = dc_lower

            # OBV (On-Balance Volume)
            indicators["obv"] = self._obv(df)

            # Historical Volatility
            indicators["historical_volatility"] = self._historical_volatility(df["close"])

            return indicators

        except Exception as e:
            logger.error("Failed to compute indicators", error=str(e))
            return {}

    def _vwap(self, df: pd.DataFrame) -> Optional[float]:
        """Volume Weighted Average Price"""
        try:
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            vwap = (typical_price * df["volume"]).sum() / df["volume"].sum()
            return float(vwap)
        except Exception:
            return None

    def _calculate_tr(self, df: pd.DataFrame) -> np.ndarray:
        """
        Calculate True Range using optimized NumPy operations.
        Returns numpy array.
        """
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr1 = high - low

        # Calculate tr2 and tr3 using previous close
        # Use roll for efficiency, but handle first element
        prev_close = np.roll(close, 1)

        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        # First element of roll is invalid (wrapped from end), so use tr1[0] for it
        # This matches standard TR definition where first period TR = High - Low
        tr2[0] = tr1[0]
        tr3[0] = tr1[0]

        return np.maximum(tr1, np.maximum(tr2, tr3))

    def _atr(self, df: pd.DataFrame, tr: Optional[np.ndarray] = None) -> Optional[float]:
        """Average True Range"""
        try:
            if tr is None:
                tr = self._calculate_tr(df)

            # Optimized using numpy rolling mean
            atr = self._rolling_mean(tr, self.atr_period)

            # Return last element if valid
            last_val = atr[-1]
            return float(last_val) if not np.isnan(last_val) else None
        except Exception:
            return None

    def _rsi(self, df: pd.DataFrame) -> Optional[float]:
        """Relative Strength Index"""
        try:
            close = df["close"].values # Convert to numpy array immediately

            # Numpy diff (prepend nan to match size)
            delta = np.diff(close, prepend=np.nan)

            # Vectorized gain/loss
            # Note: np.where propagates NaNs if delta has NaNs (which it does at index 0)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)

            # Optimized rolling mean
            avg_gain = self._rolling_mean(gain, self.rsi_period)
            avg_loss = self._rolling_mean(loss, self.rsi_period)

            # Avoid division by zero
            # If avg_loss is 0, RS is infinite -> RSI is 100
            # We handle this by checking mask or handling inf

            with np.errstate(divide='ignore', invalid='ignore'):
                 rs = avg_gain / avg_loss
                 rsi = 100 - (100 / (1 + rs))

            # If avg_loss was 0, rs is inf, rsi becomes 100.
            # If avg_gain and avg_loss both 0 (unlikely for period>1), rs is nan.

            last_val = rsi[-1]
            return float(last_val) if not np.isnan(last_val) else None
        except Exception:
            return None

    def _adx(self, df: pd.DataFrame, tr: Optional[np.ndarray] = None) -> Optional[float]:
        """Average Directional Index"""
        try:
            high = df["high"].values
            low = df["low"].values

            # Numpy diff
            # up_move = high - prev_high
            # down_move = prev_low - low

            # Using roll for shift(1)
            prev_high = np.roll(high, 1)
            prev_low = np.roll(low, 1)
            # Invalid first element logic handled by logic or explicit set

            up_move = high - prev_high
            down_move = prev_low - low

            # We must ignore the first element (garbage from roll)
            # But the subsequent logic (rolling mean) will naturally propagate if we treat it right.
            # Pandas shift puts NaN at 0.
            up_move[0] = np.nan
            down_move[0] = np.nan

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            # Calculate ATR
            if tr is None:
                tr = self._calculate_tr(df)

            # Optimized rolling mean for ATR
            atr = self._rolling_mean(tr, self.adx_period)

            # Optimized rolling mean for +DM, -DM
            plus_dm_smooth = self._rolling_mean(plus_dm, self.adx_period)
            minus_dm_smooth = self._rolling_mean(minus_dm, self.adx_period)

            with np.errstate(divide='ignore', invalid='ignore'):
                plus_di = 100 * plus_dm_smooth / atr
                minus_di = 100 * minus_dm_smooth / atr

                # Calculate DX and ADX
                dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

            adx = self._rolling_mean(dx, self.adx_period)

            last_val = adx[-1]
            return float(last_val) if not np.isnan(last_val) else None
        except Exception:
            return None

    def _ema(self, series: pd.Series, period: int) -> Optional[float]:
        """Exponential Moving Average"""
        try:
            ema = series.ewm(span=period, adjust=False).mean()
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None
        except Exception:
            return None

    def _supertrend(self, df: pd.DataFrame, tr: Optional[np.ndarray] = None) -> tuple[Optional[float], Optional[int]]:
        """
        Supertrend indicator.

        Returns:
            (supertrend_value, direction) where direction is 1 for uptrend, -1 for downtrend
        """
        try:
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values

            # Calculate ATR
            if tr is None:
                tr = self._calculate_tr(df)

            # ATR is moving average of TR
            # Optimized rolling mean
            atr = self._rolling_mean(tr, self.supertrend_period)

            # Calculate basic upper and lower bands
            hl_avg = (high + low) / 2
            basic_ub = hl_avg + (self.supertrend_multiplier * atr)
            basic_lb = hl_avg - (self.supertrend_multiplier * atr)

            # Calculate final bands
            # We must iterate because of recursive definition
            n = len(df)
            final_ub = np.zeros(n)
            final_lb = np.zeros(n)
            supertrend = np.zeros(n)
            direction = np.ones(n, dtype=int)

            # Initial values
            final_ub[0] = basic_ub[0]
            final_lb[0] = basic_lb[0]

            # Optimized loop using numpy arrays (avoiding pandas overhead)
            for i in range(1, n):
                # Final Upper Band
                # Note: nan comparisons in numpy are False.
                if np.isnan(final_ub[i-1]):
                    final_ub[i] = basic_ub[i]
                elif (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                    final_ub[i] = basic_ub[i]
                else:
                    final_ub[i] = final_ub[i-1]

                # Final Lower Band
                if np.isnan(final_lb[i-1]):
                    final_lb[i] = basic_lb[i]
                elif (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
                    final_lb[i] = basic_lb[i]
                else:
                    final_lb[i] = final_lb[i-1]

                # Supertrend
                if close[i] <= final_ub[i]:
                    supertrend[i] = final_ub[i]
                    direction[i] = -1
                else:
                    supertrend[i] = final_lb[i]
                    direction[i] = 1

            return (
                float(supertrend[-1]) if not np.isnan(supertrend[-1]) else None,
                int(direction[-1])
            )
        except Exception:
            return None, None

    def _bollinger_bands(self, series: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Bollinger Bands.

        Returns:
            (upper, middle, lower)
        """
        try:
            # We can optimize 'middle' (mean) but 'std' requires creating Series anyway unless we impl std.
            # But converting to numpy for mean saves one Series creation if passed as Series (it is).
            # Wait, series is passed as Series.
            # Using rolling mean on series is optimized C code in pandas.
            # The bottleneck was converting numpy->Series. Here input IS Series.
            # So optimization might be minimal, but let's see.
            # Actually, `series` input is `df["close"]` which is Series.
            # But let's check `compute_all`: `self._bollinger_bands(df["close"])`.
            # If we used numpy input, we might avoid overhead if we implemented `rolling_std`.
            # For now, let's leave bollinger alone as per my plan to focus on heavy hitters (ADX/ATR).
            # Wait, I said I would optimize it. But safety first.

            middle = series.rolling(window=self.bb_period).mean()
            std = series.rolling(window=self.bb_period).std()
            upper = middle + (std * self.bb_std)
            lower = middle - (std * self.bb_std)

            return (
                float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
                float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else None,
                float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None
            )
        except Exception:
            return None, None, None

    def _donchian(self, df: pd.DataFrame, period: int = 20) -> tuple[Optional[float], Optional[float]]:
        """
        Donchian Channel.

        Returns:
            (upper, lower)
        """
        try:
            upper = df["high"].rolling(window=period).max()
            lower = df["low"].rolling(window=period).min()

            return (
                float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
                float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None
            )
        except Exception:
            return None, None

    def _obv(self, df: pd.DataFrame) -> Optional[float]:
        """On-Balance Volume"""
        try:
            close = df["close"].values
            volume = df["volume"].values

            # Vectorized OBV calculation
            diff = np.diff(close, prepend=close[0])
            # Note: loop in original code started from 1, effectively treating diff[0] as 0 (no change)

            direction = np.sign(diff)
            # Ensure first element doesn't contribute (matching original logic where loop starts at 1)
            direction[0] = 0

            obv = np.cumsum(direction * volume)

            return float(obv[-1])
        except Exception:
            return None

    def _historical_volatility(self, series: pd.Series, window: int = 20) -> Optional[float]:
        """
        Calculate annualized historical volatility.
        Uses standard deviation of log returns.

        Note on IV Rank:
        IV Rank calculation requires historical implied volatility data which is not available
        in the standard OHLCV bars. It should be populated by an external service or
        a different data loader if available.
        """
        try:
            log_returns = np.log(series / series.shift(1))
            vol = log_returns.rolling(window=window).std()

            # Annualize (assuming 252 trading days)
            # For intraday bars, this scaling might need adjustment, but sticking to standard annualization for consistency
            annual_vol = vol * np.sqrt(252)

            return float(annual_vol.iloc[-1]) if not pd.isna(annual_vol.iloc[-1]) else None
        except Exception:
            return None

    def _kama(self, series: pd.Series, period: int = 10, fast: int = 2, slow: int = 30) -> Optional[float]:
        """Kaufman Adaptive Moving Average"""
        try:
            change = abs(series - series.shift(period))
            volatility = (abs(series - series.shift())).rolling(window=period).sum()

            er = change / volatility  # Efficiency Ratio

            fast_sc = 2 / (fast + 1)
            slow_sc = 2 / (slow + 1)

            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

            kama = pd.Series(0.0, index=series.index)
            kama.iloc[period-1] = series.iloc[period-1]

            for i in range(period, len(series)):
                kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (series.iloc[i] - kama.iloc[i-1])

            return float(kama.iloc[-1]) if not pd.isna(kama.iloc[-1]) else None
        except Exception:
            return None
