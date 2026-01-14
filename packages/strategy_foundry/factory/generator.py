import random
import hashlib
import json
from packages.strategy_foundry.factory.grammar import StrategyConfig, Rule
from packages.strategy_foundry.factory.parameter_space import ParameterSpace
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter
import pandas as pd
import numpy as np

class StrategyGenerator:
    def generate_candidate(self) -> StrategyConfig:
        """Generates a random strategy configuration."""

        # Simple Logic: 1 or 2 entry rules
        num_rules = random.choice([1, 2])
        entry_rules = []

        for _ in range(num_rules):
            ind = ParameterSpace.get_random_indicator()
            params = ParameterSpace.get_random_params(ind)

            # For simplicity, we compare against fixed thresholds or price
            # Logic: Indicator > Threshold

            op = random.choice(['>', '<'])

            if ind in ['ema', 'supertrend', 'bollinger', 'donchian']:
                # These are price overlays usually
                # Condition: Close > Indicator
                val = "close" # Special keyword
            else:
                # Oscillators
                val = ParameterSpace.get_random_threshold(ind)

            entry_rules.append(Rule(ind, op, val, params))

        # Exit rules: usually reverse of entry or trailing stop (handled by risk)
        # We can add explicit exit rules later. For now let's rely on stop loss / take profit / time stop.
        exit_rules = []

        sl = random.choice([1.0, 2.0, 3.0])
        tp = random.choice([2.0, 4.0, 6.0])
        max_bars = random.choice([5, 10, 20, 50])

        # Generate ID
        # We use a hash of the rules to ensure stable ID for same logic
        config_dict = {
            "entry": [vars(r) for r in entry_rules],
            "sl": sl,
            "tp": tp,
            "max_bars": max_bars
        }
        sid = hashlib.md5(json.dumps(config_dict, sort_keys=True).encode()).hexdigest()[:8]

        return StrategyConfig(
            strategy_id=sid,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            stop_loss_atr=sl,
            take_profit_atr=tp,
            max_bars_hold=max_bars
        )

    def generate_positions(self, df: pd.DataFrame, config: StrategyConfig) -> pd.Series:
        """
        Executes the strategy on a DataFrame to generate positions (-1, 0, 1).
        This is a vectorized implementation.
        """
        # 1. Compute Indicators
        # We need to compute all indicators required by rules
        # We can cache them to avoid recomputing if multiple rules use same indicator/params

        signals = pd.Series(0, index=df.index)

        # Combine Entry Rules (AND logic)
        entry_condition = pd.Series(True, index=df.index)

        for rule in config.entry_rules:
            # Get Indicator Series
            if rule.indicator == 'rsi':
                series = IndicatorsAdapter.rsi(df, **rule.params)
            elif rule.indicator == 'adx':
                series = IndicatorsAdapter.adx(df, **rule.params)
            elif rule.indicator == 'ema':
                series = IndicatorsAdapter.ema(df['close'], **rule.params)
            elif rule.indicator == 'supertrend':
                st, direction = IndicatorsAdapter.supertrend(df, **rule.params)
                # Supertrend rule usually checks direction
                # If rule.val is 'close', maybe we check close > supertrend?
                # Or checks direction directly?
                # Let's assume for supertrend we check Close > Supertrend for Long
                series = st
            elif rule.indicator == 'bollinger':
                 u, m, l = IndicatorsAdapter.bollinger_bands(df['close'], **rule.params)
                 # Usually we check Close < Lower (reversion) or Close > Upper (breakout)
                 # Let's assume we use Lower/Upper based on operator
                 if rule.operator == '<':
                     series = l # Close < Lower
                 else:
                     series = u # Close > Upper
            elif rule.indicator == 'donchian':
                u, l = IndicatorsAdapter.donchian(df, **rule.params)
                if rule.operator == '>':
                    series = u
                else:
                    series = l
            else:
                series = pd.Series(0, index=df.index) # Fallback

            # Compare
            val = rule.value
            if val == 'close':
                val_series = df['close']
            else:
                val_series = val

            # Series comparison
            # Need to align lengths? adapters return numpy arrays or series aligned with df
            # If numpy array, convert to series for alignment safety
            if isinstance(series, np.ndarray):
                series = pd.Series(series, index=df.index)

            if rule.operator == '>':
                cond = series > val_series
            elif rule.operator == '<':
                cond = series < val_series
            else:
                cond = pd.Series(False, index=df.index)

            entry_condition = entry_condition & cond

        # Generate raw signals (1 where condition met)
        # Note: This is simplified "Long Only" generation for now as per requirements

        # We want to enter when condition BECOMES true? Or while true?
        # Usually strategies trigger on crossover.
        # Let's do: True and Prev False (Crossover)
        # entry_signal = entry_condition & (~entry_condition.shift(1).fillna(False))

        # But for state persistence ("while condition true"), trend strategies might want to stay in.
        # However, the foundry instruction says "generate_positions(df) -> positions in {-1,0,1}".
        # And "Timeframe: Daily. Execution: next-bar open".

        # If I return 1, it means "I want to be long". 0 means "Flat".
        # So I should handle exits here too?
        # "apply_risk_overlay(df, positions) -> final_positions"

        # Let's generate 'signals' (1 = Buy Signal).
        # And let the engine/risk overlay handle the holding period / stops.

        # If the interface expects "Target Position", then 1 means "Hold Long".
        # If it expects "Trade Signal", then 1 means "Buy".

        # Let's make it return "Target Position" (State).
        # But stops are dynamic (based on entry price).
        # So `generate_positions` effectively generates the *Entry Signal*.
        # The `apply_risk_overlay` will simulate the trade management (holding, stops).

        entry_signal = entry_condition.astype(int)

        return entry_signal

    def apply_risk_overlay(self, df: pd.DataFrame, entry_signals: pd.Series, config: StrategyConfig) -> pd.Series:
        """
        Applies risk management (Stop Loss, Take Profit, Time Stop) to convert entry signals into actual positions.
        This is a path-dependent loop (iterative).
        """
        positions = pd.Series(0, index=df.index)

        atr = IndicatorsAdapter.atr(df, period=14) # Standard ATR for risk

        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0

        close_prices = df['close'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        atr_values = atr

        signal_values = entry_signals.values

        n = len(df)
        pos_array = np.zeros(n, dtype=int)

        for i in range(1, n):
            # Check exit if in trade
            if in_trade:
                bars_held = i - entry_idx

                # Check Time Stop
                if bars_held >= config.max_bars_hold:
                    in_trade = False
                    pos_array[i] = 0
                    continue

                # Check SL/TP
                # We check against Low/High of current bar?
                # "Execution: next-bar open".
                # So if we entered at Open of i (signal at i-1), we check price action of i.

                # Assuming signal at i means "be long at i".
                # No, standard is: Signal at i (Close), Enter Open i+1.
                # So here, `entry_signals` has 1 at i.
                # If we are in trade, we maintain 1.

                # Let's clarify: `entry_signals` has 1 where rules are met.
                # If we are NOT in trade, and signal[i-1] == 1:
                #   Enter at Open[i] (or assume Close[i-1] approx/slippage handled later).
                #   Actually, the engine handles execution.
                #   Here we just want to output the "Target Position" for bar i.

                # If I return 1 for bar i, it means "I hold position during bar i".

                current_low = low_prices[i]
                current_high = high_prices[i]

                if current_low <= stop_loss:
                    in_trade = False # Stopped out
                    pos_array[i] = 0
                elif current_high >= take_profit:
                    in_trade = False # TP hit
                    pos_array[i] = 0
                else:
                    pos_array[i] = 1 # Hold

            # Check Entry
            if not in_trade:
                # If signal was generated at i-1, we enter at i
                # Or if signal is at i, we enter next?
                # Usually signal series aligns with price. Signal at T means condition met at T.
                # So we enter at T+1.
                if signal_values[i-1] == 1:
                    in_trade = True
                    entry_price = df['open'].iloc[i] # Approximate entry at Open
                    entry_idx = i

                    # Set Stops
                    current_atr = atr_values[i-1] # Use ATR at time of signal
                    if np.isnan(current_atr):
                        current_atr = entry_price * 0.01 # Fallback 1%

                    stop_loss = entry_price - (config.stop_loss_atr * current_atr)
                    take_profit = entry_price + (config.take_profit_atr * current_atr)

                    pos_array[i] = 1

        return pd.Series(pos_array, index=df.index)

