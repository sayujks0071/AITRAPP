from typing import Dict, Any
import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

class IndicatorsAdapter:
    """
    Adapter to reuse packages.core.indicators logic with dynamic parameters.
    """

    @staticmethod
    def get_calculator(params: Dict[str, Any]) -> IndicatorCalculator:
        """
        Factory to get a calculator instance with specific parameters.
        """
        return IndicatorCalculator(
            atr_period=params.get("atr_period", 14),
            rsi_period=params.get("rsi_period", 14),
            adx_period=params.get("adx_period", 14),
            ema_fast=params.get("ema_fast", 34),
            ema_slow=params.get("ema_slow", 89),
            supertrend_period=params.get("supertrend_period", 10),
            supertrend_multiplier=params.get("supertrend_multiplier", 3.0),
            bb_period=params.get("bb_period", 20),
            bb_std=params.get("bb_std", 2.0)
        )

    @staticmethod
    def calculate_indicator(df: pd.DataFrame, indicator_name: str, params: Dict[str, Any]) -> Any:
        """
        Calculate a specific indicator series.
        """
        calc = IndicatorsAdapter.get_calculator(params)

        if indicator_name == "rsi":
            return calc.rsi_series(df)
        elif indicator_name == "atr":
            return calc.atr_series(df)
        elif indicator_name == "adx":
            return calc.adx_series(df)
        elif indicator_name == "ema_fast":
            return calc.ema_series(df["close"], calc.ema_fast)
        elif indicator_name == "ema_slow":
            return calc.ema_series(df["close"], calc.ema_slow)
        elif indicator_name == "supertrend":
            return calc.supertrend_series(df)
        elif indicator_name == "bollinger":
            return calc.bollinger_bands_series(df["close"])
        elif indicator_name == "donchian":
            return calc.donchian_series(df, period=params.get("donchian_period", 20))
        else:
            raise ValueError(f"Unknown indicator: {indicator_name}")
