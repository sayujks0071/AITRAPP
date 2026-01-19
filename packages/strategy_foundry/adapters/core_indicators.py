"""
Adapter for core indicators.
Reuses `packages.core.indicators.IndicatorCalculator` to ensure consistency.
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

class IndicatorsAdapter:
    def __init__(self):
        # We initialize with default params, but many methods below might override or compute specifically.
        # The core calculator is stateful regarding periods initialized in __init__.
        # For strategy foundry, we might want dynamic periods per call or per strategy instance.
        # However, the core `compute_all` uses the init params.
        # So we might need to instantiate IndicatorCalculator per strategy or use its low-level methods.
        pass

    def compute_all_with_params(self, df: pd.DataFrame, params: Dict[str, int]) -> Dict[str, float]:
        """
        Compute indicators using specific parameters.
        This instantiates a new calculator for the specific params.
        """
        calc = IndicatorCalculator(
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
        return calc.compute_all(df)

    # Expose individual vectorized series calculations for the backtest engine
    # We use a default calculator instance for access to methods that don't depend on self state or where we pass it.
    # Actually, most methods in IndicatorCalculator use self.* params.
    # So we should likely create a calculator instance on the fly or allow passing it.

    @staticmethod
    def get_calculator(params: Dict[str, any]) -> IndicatorCalculator:
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

