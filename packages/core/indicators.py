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
