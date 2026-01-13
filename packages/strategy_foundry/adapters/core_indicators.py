import numpy as np
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class VectorizedIndicators(IndicatorCalculator):
    """
    Adapter to expose full series calculations from IndicatorCalculator logic.
    Optimized for backtesting over full history.
    """

    def get_atr(self, df: pd.DataFrame) -> pd.Series:
        tr = self._calculate_tr(df)
        atr_arr = self._rolling_mean(tr, self.atr_period)
        return pd.Series(atr_arr, index=df.index)

    def get_rsi(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"].values
        delta = np.diff(close, prepend=np.nan)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        # Use simple moving average as in core (or Wilder's? Core uses simple rolling mean)
        # Core: self._rolling_mean(gain, self.rsi_period)
        avg_gain = self._rolling_mean(gain, self.rsi_period)
        avg_loss = self._rolling_mean(loss, self.rsi_period)

        with np.errstate(divide='ignore', invalid='ignore'):
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        return pd.Series(rsi, index=df.index)

    def get_adx(self, df: pd.DataFrame) -> pd.Series:
        tr = self._calculate_tr(df)
        high = df["high"].values
        low = df["low"].values

        prev_high = np.roll(high, 1)
        prev_low = np.roll(low, 1)

        up_move = high - prev_high
        down_move = prev_low - low

        up_move[0] = np.nan
        down_move[0] = np.nan

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        atr = self._rolling_mean(tr, self.adx_period)
        plus_dm_smooth = self._rolling_mean(plus_dm, self.adx_period)
        minus_dm_smooth = self._rolling_mean(minus_dm, self.adx_period)

        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        adx = self._rolling_mean(dx, self.adx_period)
        return pd.Series(adx, index=df.index)

    def get_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def get_supertrend(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """Returns (supertrend_line, direction)"""
        # We can't reuse the core single-value logic easily because it iterates.
        # But core actually iterates over the whole array in _supertrend!
        # It just returns the last value.
        # So we can just copy-paste that logic and return the arrays.

        tr = self._calculate_tr(df)
        atr = self._rolling_mean(tr, self.supertrend_period)

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (self.supertrend_multiplier * atr)
        basic_lb = hl_avg - (self.supertrend_multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n, dtype=int)

        # Initial values
        final_ub[0] = basic_ub[0]
        final_lb[0] = basic_lb[0]

        for i in range(1, n):
            if np.isnan(final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            elif (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

            if np.isnan(final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            elif (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]

            if close[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
                direction[i] = -1
            else:
                supertrend[i] = final_lb[i]
                direction[i] = 1

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def get_bollinger(self, series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=self.bb_period).mean()
        std = series.rolling(window=self.bb_period).std()
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        return upper, middle, lower

    def get_donchian(self, df: pd.DataFrame, period=20) -> tuple[pd.Series, pd.Series]:
        upper = df["high"].rolling(window=period).max()
        lower = df["low"].rolling(window=period).min()
        return upper, lower

