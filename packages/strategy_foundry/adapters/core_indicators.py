"""Adapter for core indicators to strategy blocks"""
import pandas as pd
import numpy as np
from typing import Dict
from packages.core.indicators import IndicatorCalculator
from packages.strategy_foundry.factory.grammar import StrategyBlock

class IndicatorsAdapter:
    def __init__(self):
        self.calc = IndicatorCalculator()

    def compute_for_blocks(self, df: pd.DataFrame, block: StrategyBlock):
        """
        Compute indicators needed for a block and attach to df.
        """
        params = block.params
        name = block.name

        if name == "DonchianBreakout":
            period = params["period"]
            # We need high/low rolling max/min
            df[f"dc_upper_{period}"] = df["high"].rolling(period).max()
            df[f"dc_lower_{period}"] = df["low"].rolling(period).min()

        elif name == "EMACross":
            fast = params["fast_period"]
            slow = params["slow_period"]
            df[f"ema_{fast}"] = df["close"].ewm(span=fast, adjust=False).mean()
            df[f"ema_{slow}"] = df["close"].ewm(span=slow, adjust=False).mean()

        elif name == "RSIReversion":
            period = params["period"]
            # Use core lib if possible, but it returns float (last val) or needs adaptation.
            # Core lib has rsi_series method.
            df[f"rsi_{period}"] = self.calc.rsi_series(df.rename(columns={"close":"close"})) # Ensure types match if needed?
            # Note: `rsi_series` creates a new object, not utilizing `period` arg if class initialized differently?
            # Core `IndicatorCalculator` takes params in init. We need dynamic.
            # Let's just implement or monkey-patch locally for dynamic periods if core doesn't support dynamic series well.
            # Core `rsi_series` uses `self.rsi_period`.
            # So we should probably instantiate a calculator with right params or just implement here.

            # Implementation of RSI here for dynamic period:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        elif name == "ATRStop" or name == "VolatilityFilter":
            # ATR needed
            if "atr_period" in params:
                period = params["atr_period"]
            elif "period" in params:
                period = params["period"]
            else:
                period = 14

            # Simple ATR calc
            high = df["high"]
            low = df["low"]
            close = df["close"]
            tr = pd.concat([high - low,
                            (high - close.shift()).abs(),
                            (low - close.shift()).abs()], axis=1).max(axis=1)
            df[f"atr_{period}"] = tr.rolling(period).mean()

        elif name == "TrendFilterEMA":
             period = params["period"]
             df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()

    def evaluate_condition(self, df: pd.DataFrame, block: StrategyBlock) -> pd.Series:
        """
        Evaluate entry/filter logic returning boolean series.
        """
        params = block.params
        name = block.name

        if name == "DonchianBreakout":
            period = params["period"]
            # Close > Upper Channel of PREVIOUS bar (to avoid lookahead bias if using current)
            # Standard Donchian: Enter if price breaks previous N days high.
            # Here we check if Close > Shifted Max High
            upper = df[f"dc_upper_{period}"].shift(1)
            return df["close"] > upper

        elif name == "EMACross":
            fast = params["fast_period"]
            slow = params["slow_period"]
            # Fast crosses above Slow
            ema_f = df[f"ema_{fast}"]
            ema_s = df[f"ema_{slow}"]
            return (ema_f > ema_s) & (ema_f.shift(1) <= ema_s.shift(1))

        elif name == "RSIReversion":
            period = params["period"]
            lower = params["lower_threshold"]
            # RSI crosses above lower threshold (Mean Reversion Long)
            rsi = df[f"rsi_{period}"]
            return (rsi < lower) & (rsi.shift(1) >= lower) # Actually dip below?
            # Reversion usually: Price drops, RSI < 30. Enter.
            # Or enter when it crosses BACK above 30?
            # Let's do: RSI < Lower (Oversold) -> Enter Long
            return rsi < lower

        elif name == "TrendFilterEMA":
            period = params["period"]
            ema = df[f"ema_{period}"]
            return df["close"] > ema

        elif name == "VolatilityFilter":
            period = params["atr_period"]
            percentile = params["percentile"]
            atr = df[f"atr_{period}"]
            # Calculate rolling percentile of ATR over last 500 bars?
            # Or just check if ATR is high enough?
            # "Regime filter: ATR percentile regime"
            # Let's compute rolling quantile
            atr_rank = atr.rolling(500).rank(pct=True)
            return atr_rank > (percentile / 100.0)

        # Default True if unknown (or False?)
        return pd.Series(True, index=df.index)
