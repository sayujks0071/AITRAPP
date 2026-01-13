import pandas as pd
import numpy as np
from typing import Dict, Any, List
import random
import hashlib
import json
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.factory.grammar import Grammar

# Re-export StrategyGenerator from grammar if it was defined there,
# but actually I defined StrategyGenerator in grammar.py in the previous step (Wait, let me check).
# I wrote grammar.py with StrategyGenerator inside it.
# Then I wrote generator.py with GeneratedStrategy inside it.
# But run_hourly tries to import StrategyGenerator from generator.py.

# I should move StrategyGenerator to generator.py OR import it.

class StrategyGenerator:
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)

    def generate_candidates(self, n: int) -> List[Dict[str, Any]]:
        candidates = []
        seen = set()

        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            strat = Grammar.generate_random_strategy()
            if strat["id"] not in seen:
                seen.add(strat["id"])
                candidates.append(strat)
            attempts += 1

        return candidates

class GeneratedStrategy:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.id = config["id"]
        self.indicators = VectorizedIndicators()

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generates positions (1, 0, -1) for the dataframe.
        """
        entry = self.config["entry"]
        filt = self.config.get("filter")

        # 1. Entry Logic
        entry_signal = self._evaluate_entry(df, entry)

        # 2. Filter Logic
        signals = self._get_raw_signals(df, entry) # 1 = Buy, -1 = Sell

        if filt:
            f_mask = self._evaluate_filter(df, filt)
            signals = np.where((signals == 1) & (~f_mask), 0, signals)

        # Exits
        exit_conf = self.config["exit"]

        positions = np.zeros(len(df))
        in_trade = False
        entry_price = 0.0
        entry_idx = 0

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        atr = None
        if exit_conf["name"] == "atr_stop":
            atr = self.indicators.get_atr(df).values

        # Logic loop
        for i in range(1, len(df)):
            positions[i] = positions[i-1]

            if in_trade:
                hit_stop = False
                if exit_conf["name"] == "atr_stop":
                    stop_dist = atr[entry_idx] * exit_conf["params"]["multiplier"]
                    stop_price = entry_price - stop_dist
                    if low[i] < stop_price:
                        hit_stop = True

                elif exit_conf["name"] == "time_stop":
                    if (i - entry_idx) >= exit_conf["params"]["days"]:
                        hit_stop = True

                if hit_stop:
                    positions[i] = 0
                    in_trade = False
                    continue

                if signals[i] == -1:
                    positions[i] = 0
                    in_trade = False
                    continue

            if not in_trade:
                if signals[i] == 1:
                    positions[i] = 1
                    in_trade = True
                    entry_price = close[i]
                    entry_idx = i

        return pd.Series(positions, index=df.index)

    def _evaluate_entry(self, df: pd.DataFrame, entry_conf: Dict) -> Any:
        # Not used, relying on _get_raw_signals
        pass

    def _get_raw_signals(self, df: pd.DataFrame, entry_conf: Dict) -> np.ndarray:
        """Returns 1 (Buy), -1 (Sell), 0 (Neutral) based on Entry logic."""
        name = entry_conf["name"]
        params = entry_conf["params"]
        n = len(df)
        signals = np.zeros(n)

        if name == "ema_cross":
            fast = self.indicators.get_ema(df["close"], params["fast"])
            slow = self.indicators.get_ema(df["close"], params["slow"])
            cond = (fast > slow)
            signals = np.where(cond, 1, -1)

        elif name == "supertrend":
            self.indicators.supertrend_period = params["period"]
            self.indicators.supertrend_multiplier = params["multiplier"]
            st, direction = self.indicators.get_supertrend(df)
            signals = direction.values # 1 or -1

        elif name == "donchian_breakout":
            up, lo = self.indicators.get_donchian(df, params["period"])
            close = df["close"].values
            prev_up = up.shift(1).values
            prev_lo = lo.shift(1).values

            signals = np.zeros(n)
            signals = np.where(close > prev_up, 1, signals)
            signals = np.where(close < prev_lo, -1, signals)
            # Fill logic handled by loop propagation?
            # Donchian usually implies holding.
            # We return state 1/-1.
            s_series = pd.Series(signals).replace(0, np.nan).ffill().fillna(0)
            signals = s_series.values

        elif name == "rsi_reversion":
            rsi = self.indicators.get_rsi(df).values
            signals = np.zeros(n)
            signals = np.where(rsi < params["buy_threshold"], 1, signals)
            signals = np.where(rsi > params["sell_threshold"], -1, signals)

        elif name == "bollinger_reversion":
            self.indicators.bb_period = params["period"]
            self.indicators.bb_std = params["std"]
            up, mid, lo = self.indicators.get_bollinger(df["close"])
            close = df["close"].values

            signals = np.zeros(n)
            signals = np.where(close < lo, 1, signals)
            signals = np.where(close > up, -1, signals)

        return signals

    def _evaluate_filter(self, df: pd.DataFrame, filter_conf: Dict) -> np.ndarray:
        name = filter_conf["name"]
        params = filter_conf["params"]

        if name == "adx_filter":
            adx = self.indicators.get_adx(df).values
            return adx > params["threshold"]

        elif name == "regime_filter":
            sma = df["close"].rolling(params["ma_period"]).mean().values
            return df["close"].values > sma

        return np.ones(len(df), dtype=bool)
