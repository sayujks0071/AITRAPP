import random
import hashlib
import json
from typing import Any, Dict
import pandas as pd
import numpy as np
from packages.strategy_foundry.factory.grammar import StrategyConfig, Rule, Filter
from packages.strategy_foundry.factory.parameter_space import ParameterSpace
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class StrategyGenerator:
    def generate_candidate(self) -> StrategyConfig:
        """Generates a random strategy configuration using grammar blocks."""

        # 1. Choose Entry Logic (1-2 blocks)
        entry_logic_type = random.choice(['breakout', 'trend', 'reversion', 'volatility_expansion'])
        entry_rules = []

        if entry_logic_type == 'breakout':
            # Donchian Breakout or Bollinger Breakout
            if random.random() < 0.5:
                # Donchian High Breakout
                period = random.choice([20, 55])
                entry_rules.append(Rule('breakout', 'donchian', {'period': period}, '>', 'upper'))
            else:
                # BB Breakout
                params = ParameterSpace.get_random_params('bollinger')
                entry_rules.append(Rule('breakout', 'bollinger', params, '>', 'upper'))

        elif entry_logic_type == 'trend':
            # EMA Cross or Supertrend
            if random.random() < 0.5:
                # Price > EMA (Trend Long)
                params = ParameterSpace.get_random_params('ema')
                # Condition: EMA < Close (Price is above EMA)
                entry_rules.append(Rule('trend', 'ema', params, '<', 'close'))
            else:
                # Supertrend Bullish
                params = ParameterSpace.get_random_params('supertrend')
                entry_rules.append(Rule('trend', 'supertrend', params, '==', 1)) # direction == 1 (Bullish)

        elif entry_logic_type == 'reversion':
            # RSI Oversold or BB Lower bounce
            if random.random() < 0.5:
                params = ParameterSpace.get_random_params('rsi')
                thresh = random.choice([30, 40])
                entry_rules.append(Rule('reversion', 'rsi', params, '<', thresh))
            else:
                params = ParameterSpace.get_random_params('bollinger')
                entry_rules.append(Rule('reversion', 'bollinger', params, '<', 'lower')) # Close < Lower

        elif entry_logic_type == 'volatility_expansion':
             # ATR Channel Break or Range Expansion?
             # Let's say Close > Open + ATR * X (Big Bullish Candle)
             # Or simply Volatility Breakout (Close > EMA + ATR)
             # Let's implement Keltner-like: Close > EMA + 2*ATR
             # Simpler: Range Expansion: High - Low > ATR(14) * 1.5
             # But our Rule system is simpler.
             # Let's do: Close > Donchian Upper (20) AND ADX > 25
             entry_rules.append(Rule('breakout', 'donchian', {'period': 20}, '>', 'upper'))
             entry_rules.append(Rule('volatility', 'adx', {'period': 14}, '>', 25))


        # 2. Add Filters (0-2)
        filters = []
        if random.random() < 0.5:
            # ADX Filter (Trend Strength)
            params = ParameterSpace.get_random_params('adx')
            thresh = random.choice([20, 25])
            filters.append(Filter('volatility', 'adx', params, '>', thresh))

        if random.random() < 0.3:
            # Higher Timeframe Trend Filter
            # Since we only have current timeframe data in backtest engine usually,
            # this is "derived" HTF (e.g. 50 EMA on 5x period).
            # e.g. 5m -> 1h (x12). 20 EMA on 1h ~= 240 EMA on 5m.
            # Let's just add a long EMA filter.
            filters.append(Filter('regime', 'ema', {'period': 200}, '<', 'close'))

        # 3. Risk Params
        sl = random.choice([1.0, 1.5, 2.0, 3.0])
        tp = random.choice([2.0, 3.0, 4.0, 5.0])

        # Intraday horizons: 5m bars.
        # 12 bars = 1h. 75 bars = 6.25h (Full day).
        max_bars = random.choice([12, 24, 36, 75])

        # Generate ID
        config_dict = {
            "entry": [vars(r) for r in entry_rules],
            "filters": [vars(f) for f in filters],
            "sl": sl,
            "tp": tp,
            "max_bars": max_bars
        }
        sid = hashlib.md5(json.dumps(config_dict, sort_keys=True).encode()).hexdigest()[:8]

        return StrategyConfig(
            strategy_id=sid,
            entry_rules=entry_rules,
            filters=filters,
            stop_loss_atr=sl,
            take_profit_atr=tp,
            trailing_stop_atr=None,
            max_bars_hold=max_bars
        )

    def generate_signal(self, df: pd.DataFrame, config: StrategyConfig) -> pd.Series:
        """
        Generates Entry Signal (1 = Buy, 0 = None).
        """
        # Base Signal
        signal = pd.Series(True, index=df.index)

        # Apply Entry Rules
        for rule in config.entry_rules:
            cond = self._evaluate_condition(df, rule.indicator, rule.operator, rule.threshold, rule.params)
            signal = signal & cond

        # Apply Filters
        for filt in config.filters:
            cond = self._evaluate_condition(df, filt.indicator, filt.operator, filt.threshold, filt.params)
            signal = signal & cond

        # Convert boolean to integer signal (1)
        return signal.astype(int)

    def _evaluate_condition(self, df: pd.DataFrame, indicator: str, operator: str, threshold: Any, params: Dict) -> pd.Series:
        # Special composite handling first
        if indicator == 'bollinger':
            u, m, l = IndicatorsAdapter.bollinger_bands(df['close'], **params)
            if threshold == 'upper':
                return df['close'] > u if operator == '>' else df['close'] < u
            elif threshold == 'lower':
                return df['close'] < l if operator == '<' else df['close'] > l

        if indicator == 'donchian':
            u, l = IndicatorsAdapter.donchian(df, **params)
            if threshold == 'upper':
                 return df['close'] > u if operator == '>' else df['close'] < u
            elif threshold == 'lower':
                 return df['close'] < l if operator == '<' else df['close'] > l

        # Standard LHS
        if indicator == 'close':
            lhs = df['close']
        elif indicator == 'rsi':
            lhs = IndicatorsAdapter.rsi(df, **params)
        elif indicator == 'adx':
            lhs = IndicatorsAdapter.adx(df, **params)
        elif indicator == 'ema':
            lhs = IndicatorsAdapter.ema(df['close'], **params)
        elif indicator == 'supertrend':
            st, direction = IndicatorsAdapter.supertrend(df, **params)
            if threshold == 1 or threshold == -1:
                lhs = direction
            else:
                lhs = st
        else:
            lhs = pd.Series(0, index=df.index)

        # Standard RHS
        if threshold == 'close':
            rhs = df['close']
        else:
            rhs = threshold

        # Comparison
        if operator == '>':
            return lhs > rhs
        elif operator == '<':
            return lhs < rhs
        elif operator == '==':
            return lhs == rhs

        return pd.Series(False, index=df.index)
