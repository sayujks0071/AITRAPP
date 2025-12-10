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
            
            # VWAP (reset daily in production)
            indicators["vwap"] = self._vwap(df)
            
            # ATR
            indicators["atr"] = self._atr(df)
            
            # RSI
            indicators["rsi"] = self._rsi(df)
            
            # ADX
            indicators["adx"] = self._adx(df)
            
            # EMAs
            indicators["ema_fast"] = self._ema(df["close"], self.ema_fast)
            indicators["ema_slow"] = self._ema(df["close"], self.ema_slow)
            
            # Supertrend
            st_val, st_dir = self._supertrend(df)
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
            
            # MACD
            macd_line, signal_line, histogram = self._macd(df["close"])
            indicators["macd"] = macd_line
            indicators["macd_signal"] = signal_line
            indicators["macd_histogram"] = histogram
            
            # Stochastic Oscillator
            stoch_k, stoch_d = self._stochastic(df)
            indicators["stoch_k"] = stoch_k
            indicators["stoch_d"] = stoch_d
            
            # Commodity Channel Index (CCI)
            indicators["cci"] = self._cci(df)
            
            # Parabolic SAR
            indicators["sar"] = self._parabolic_sar(df)
            
            # Ichimoku Cloud (simplified - key components)
            ichi_tenkan, ichi_kijun, ichi_senkou_a, ichi_senkou_b = self._ichimoku(df)
            indicators["ichi_tenkan"] = ichi_tenkan
            indicators["ichi_kijun"] = ichi_kijun
            indicators["ichi_senkou_a"] = ichi_senkou_a
            indicators["ichi_senkou_b"] = ichi_senkou_b
            
            # Pivot Points
            pivot, r1, r2, s1, s2 = self._pivot_points(df)
            indicators["pivot"] = pivot
            indicators["pivot_r1"] = r1
            indicators["pivot_r2"] = r2
            indicators["pivot_s1"] = s1
            indicators["pivot_s2"] = s2
            
            return indicators
        
        except Exception as e:
            logger.error("Failed to compute indicators", error=str(e))
            return {}
    
    def _vwap(self, df: pd.DataFrame) -> Optional[float]:
        """Volume Weighted Average Price"""
        try:
            volume_sum = df["volume"].sum()
            if volume_sum == 0:
                # No volume data, return None instead of NaN
                return None
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            vwap = (typical_price * df["volume"]).sum() / volume_sum
            return float(vwap)
        except:
            return None
    
    def _atr(self, df: pd.DataFrame) -> Optional[float]:
        """Average True Range"""
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=self.atr_period).mean()
            
            return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
        except:
            return None
    
    def _rsi(self, df: pd.DataFrame) -> Optional[float]:
        """Relative Strength Index"""
        try:
            close = df["close"]
            delta = close.diff()
            
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except:
            return None
    
    def _adx(self, df: pd.DataFrame) -> Optional[float]:
        """Average Directional Index"""
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            # Calculate +DM and -DM
            up_move = high - high.shift()
            down_move = low.shift() - low
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            # Calculate ATR
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=self.adx_period).mean()
            
            # Calculate +DI and -DI
            plus_di = 100 * pd.Series(plus_dm).rolling(window=self.adx_period).mean() / atr
            minus_di = 100 * pd.Series(minus_dm).rolling(window=self.adx_period).mean() / atr
            
            # Calculate DX and ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=self.adx_period).mean()
            
            return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None
        except:
            return None
    
    def _ema(self, series: pd.Series, period: int) -> Optional[float]:
        """Exponential Moving Average"""
        try:
            ema = series.ewm(span=period, adjust=False).mean()
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None
        except:
            return None
    
    def _supertrend(self, df: pd.DataFrame) -> tuple[Optional[float], Optional[int]]:
        """
        Supertrend indicator.
        
        Returns:
            (supertrend_value, direction) where direction is 1 for uptrend, -1 for downtrend
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            # Calculate ATR
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=self.supertrend_period).mean()
            
            # Calculate basic upper and lower bands
            hl_avg = (high + low) / 2
            basic_ub = hl_avg + (self.supertrend_multiplier * atr)
            basic_lb = hl_avg - (self.supertrend_multiplier * atr)
            
            # Calculate final bands
            final_ub = pd.Series(0.0, index=df.index)
            final_lb = pd.Series(0.0, index=df.index)
            
            for i in range(len(df)):
                if i == 0:
                    final_ub.iloc[i] = basic_ub.iloc[i]
                    final_lb.iloc[i] = basic_lb.iloc[i]
                else:
                    final_ub.iloc[i] = basic_ub.iloc[i] if (basic_ub.iloc[i] < final_ub.iloc[i-1]) or (close.iloc[i-1] > final_ub.iloc[i-1]) else final_ub.iloc[i-1]
                    final_lb.iloc[i] = basic_lb.iloc[i] if (basic_lb.iloc[i] > final_lb.iloc[i-1]) or (close.iloc[i-1] < final_lb.iloc[i-1]) else final_lb.iloc[i-1]
            
            # Determine supertrend
            supertrend = pd.Series(0.0, index=df.index)
            direction = pd.Series(1, index=df.index)
            
            for i in range(len(df)):
                if i == 0:
                    supertrend.iloc[i] = final_ub.iloc[i]
                    direction.iloc[i] = -1
                else:
                    if close.iloc[i] <= final_ub.iloc[i]:
                        supertrend.iloc[i] = final_ub.iloc[i]
                        direction.iloc[i] = -1
                    else:
                        supertrend.iloc[i] = final_lb.iloc[i]
                        direction.iloc[i] = 1
            
            return (
                float(supertrend.iloc[-1]) if not pd.isna(supertrend.iloc[-1]) else None,
                int(direction.iloc[-1])
            )
        except:
            return None, None
    
    def _bollinger_bands(self, series: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Bollinger Bands.
        
        Returns:
            (upper, middle, lower)
        """
        try:
            middle = series.rolling(window=self.bb_period).mean()
            std = series.rolling(window=self.bb_period).std()
            upper = middle + (std * self.bb_std)
            lower = middle - (std * self.bb_std)
            
            return (
                float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
                float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else None,
                float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None
            )
        except:
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
        except:
            return None, None
    
    def _macd(self, series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        MACD (Moving Average Convergence Divergence).
        
        Returns:
            (macd_line, signal_line, histogram)
        """
        try:
            ema_fast = series.ewm(span=fast, adjust=False).mean()
            ema_slow = series.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return (
                float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None,
                float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None,
                float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None
            )
        except:
            return None, None, None
    
    def _obv(self, df: pd.DataFrame) -> Optional[float]:
        """On-Balance Volume"""
        try:
            close = df["close"]
            volume = df["volume"]
            
            obv = pd.Series(0.0, index=df.index)
            
            for i in range(1, len(df)):
                if close.iloc[i] > close.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
                elif close.iloc[i] < close.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]
            
            return float(obv.iloc[-1])
        except:
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
        except:
            return None
    
    def _stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple[Optional[float], Optional[float]]:
        """
        Stochastic Oscillator.
        
        Returns:
            (stoch_k, stoch_d) where K is %K and D is %D
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            stoch_k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            stoch_d = stoch_k.rolling(window=d_period).mean()
            
            return (
                float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else None,
                float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else None
            )
        except:
            return None, None
    
    def _cci(self, df: pd.DataFrame, period: int = 20) -> Optional[float]:
        """Commodity Channel Index"""
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            typical_price = (high + low + close) / 3
            sma_tp = typical_price.rolling(window=period).mean()
            mean_deviation = typical_price.rolling(window=period).apply(
                lambda x: abs(x - x.mean()).mean()
            )
            
            cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
            
            return float(cci.iloc[-1]) if not pd.isna(cci.iloc[-1]) else None
        except:
            return None
    
    def _parabolic_sar(self, df: pd.DataFrame, af_start: float = 0.02, af_increment: float = 0.02, af_max: float = 0.2) -> Optional[float]:
        """
        Parabolic SAR (Stop and Reverse).
        
        Returns:
            SAR value
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            sar = pd.Series(0.0, index=df.index)
            trend = pd.Series(1, index=df.index)  # 1 = uptrend, -1 = downtrend
            af = pd.Series(af_start, index=df.index)
            ep = pd.Series(0.0, index=df.index)  # Extreme point
            
            # Initialize
            sar.iloc[0] = low.iloc[0]
            ep.iloc[0] = high.iloc[0]
            
            for i in range(1, len(df)):
                if trend.iloc[i-1] == 1:  # Uptrend
                    sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
                    sar.iloc[i] = min(sar.iloc[i], low.iloc[i-1], low.iloc[i-2] if i >= 2 else low.iloc[i-1])
                    
                    if high.iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = high.iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + af_increment, af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
                    
                    if low.iloc[i] < sar.iloc[i]:
                        trend.iloc[i] = -1
                        sar.iloc[i] = ep.iloc[i-1]
                        ep.iloc[i] = low.iloc[i]
                        af.iloc[i] = af_start
                    else:
                        trend.iloc[i] = 1
                else:  # Downtrend
                    sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
                    sar.iloc[i] = max(sar.iloc[i], high.iloc[i-1], high.iloc[i-2] if i >= 2 else high.iloc[i-1])
                    
                    if low.iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = low.iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + af_increment, af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
                    
                    if high.iloc[i] > sar.iloc[i]:
                        trend.iloc[i] = 1
                        sar.iloc[i] = ep.iloc[i-1]
                        ep.iloc[i] = high.iloc[i]
                        af.iloc[i] = af_start
                    else:
                        trend.iloc[i] = -1
            
            return float(sar.iloc[-1]) if not pd.isna(sar.iloc[-1]) else None
        except:
            return None
    
    def _ichimoku(self, df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Ichimoku Cloud (key components).
        
        Returns:
            (tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            
            # Tenkan-sen (Conversion Line)
            tenkan_high = high.rolling(window=tenkan).max()
            tenkan_low = low.rolling(window=tenkan).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2
            
            # Kijun-sen (Base Line)
            kijun_high = high.rolling(window=kijun).max()
            kijun_low = low.rolling(window=kijun).min()
            kijun_sen = (kijun_high + kijun_low) / 2
            
            # Senkou Span A (Leading Span A)
            senkou_span_a = (tenkan_sen + kijun_sen) / 2
            
            # Senkou Span B (Leading Span B)
            senkou_b_high = high.rolling(window=senkou_b).max()
            senkou_b_low = low.rolling(window=senkou_b).min()
            senkou_span_b = (senkou_b_high + senkou_b_low) / 2
            
            return (
                float(tenkan_sen.iloc[-1]) if not pd.isna(tenkan_sen.iloc[-1]) else None,
                float(kijun_sen.iloc[-1]) if not pd.isna(kijun_sen.iloc[-1]) else None,
                float(senkou_span_a.iloc[-1]) if not pd.isna(senkou_span_a.iloc[-1]) else None,
                float(senkou_span_b.iloc[-1]) if not pd.isna(senkou_span_b.iloc[-1]) else None
            )
        except:
            return None, None, None, None
    
    def _pivot_points(self, df: pd.DataFrame) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Pivot Points (using previous day's high, low, close).
        
        Returns:
            (pivot, r1, r2, s1, s2)
        """
        try:
            if len(df) < 2:
                return None, None, None, None, None
            
            # Use previous day's data
            prev_high = df["high"].iloc[-2] if len(df) >= 2 else df["high"].iloc[-1]
            prev_low = df["low"].iloc[-2] if len(df) >= 2 else df["low"].iloc[-1]
            prev_close = df["close"].iloc[-2] if len(df) >= 2 else df["close"].iloc[-1]
            
            pivot = (prev_high + prev_low + prev_close) / 3
            r1 = 2 * pivot - prev_low
            r2 = pivot + (prev_high - prev_low)
            s1 = 2 * pivot - prev_high
            s2 = pivot - (prev_high - prev_low)
            
            return (
                float(pivot),
                float(r1),
                float(r2),
                float(s1),
                float(s2)
            )
        except:
            return None, None, None, None, None
