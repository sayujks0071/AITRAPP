import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

class IndicatorsAdapter:
    """
    Adapter for core indicators.
    Allows strategies to compute indicators with specific parameters.
    """

    @staticmethod
    def rsi(df: pd.DataFrame, period=14):
        calc = IndicatorCalculator(rsi_period=period)
        return calc.rsi_series(df)

    @staticmethod
    def atr(df: pd.DataFrame, period=14):
        calc = IndicatorCalculator(atr_period=period)
        return calc.atr_series(df)

    @staticmethod
    def adx(df: pd.DataFrame, period=14):
        calc = IndicatorCalculator(adx_period=period)
        return calc.adx_series(df)

    @staticmethod
    def ema(series: pd.Series, period=34):
        calc = IndicatorCalculator() # Period passed to method
        return calc.ema_series(series, period)

    @staticmethod
    def supertrend(df: pd.DataFrame, period=10, multiplier=3.0):
        calc = IndicatorCalculator(supertrend_period=period, supertrend_multiplier=multiplier)
        return calc.supertrend_series(df)

    @staticmethod
    def bollinger_bands(series: pd.Series, period=20, std=2.0):
        calc = IndicatorCalculator(bb_period=period, bb_std=std)
        return calc.bollinger_bands_series(series)

    @staticmethod
    def donchian(df: pd.DataFrame, period=20):
        calc = IndicatorCalculator()
        return calc.donchian_series(df, period=period)
