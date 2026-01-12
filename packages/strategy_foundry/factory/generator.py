import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.adapters.core_indicators import calculate_indicators

class StrategyImpl:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate target positions (-1, 0, 1) for the dataframe.
        """
        # Calculate indicators needed
        df = calculate_indicators(df, self.config.params)

        # Initialize signals
        signals = pd.Series(0, index=df.index)

        # We need to maintain state for some strategies (e.g. stops),
        # but for vectorized entry signals, we can do it at once.
        # Exits often require loop if they depend on entry price.
        # However, for pure vectorization, we often approximate or use a hybrid approach.
        # Requirement: "Unified interface... generate_positions(df) -> positions"
        # To strictly support complex stops (trailing, ATR based on entry), we might need iteration.
        # But let's try to keep it vectorized if possible, or use a fast loop.
        # Given "Backtest engine... execution: next-bar open", we produce SIGNALS here.

        # Let's separate Entry Logic and Exit Logic.

        entries = self._compute_entries(df)

        # Apply Exits / Risk Overlay
        # This transforms entry signals into actual positions held
        positions = self._apply_risk_overlay(df, entries)

        return positions

    def _compute_entries(self, df: pd.DataFrame) -> pd.Series:
        # 1 for Long Entry, -1 for Short Entry, 0 for nothing
        entries = pd.Series(0, index=df.index)

        # Check Entry Blocks
        for b in self.config.blocks:
            if b['type'] == 'trend':
                if b['subtype'] == 'ema_cross':
                    # Crossover logic
                    fast = df['ema_50'] # default names from adapter?
                    # Adapter hardcodes ema_50, ema_200.
                    # We need dynamic params support in adapter or custom calculation here.
                    # Let's assume adapter was just a helper and we might calculate ad-hoc if needed.
                    # Or we update adapter to use params. Adapter uses params passed to it.
                    # But adapter writes to fixed column names?
                    # Let's fix adapter usage.

                    # Actually, for simplicity, let's recalculate specific EMAs if params differ.
                    p_fast = self.config.params.get('ema_fast', 50)
                    p_slow = self.config.params.get('ema_slow', 200)

                    ema_fast = df['close'].ewm(span=p_fast, adjust=False).mean()
                    ema_slow = df['close'].ewm(span=p_slow, adjust=False).mean()

                    # Entry: Fast crosses above Slow
                    long_cond = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
                    short_cond = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

                    entries[long_cond] = 1
                    entries[short_cond] = -1

                elif b['subtype'] == 'supertrend':
                    # Direction is in 'supertrend' (value) vs Close?
                    st = df['supertrend']
                    # Supertrend is the trailing stop line.
                    # If Close > Supertrend, Uptrend.
                    # If Close < Supertrend, Downtrend.

                    entries[df['close'] > st] = 1
                    entries[df['close'] < st] = -1

                elif b['subtype'] == 'donchian':
                    # Breakout
                    period = self.config.params.get('donchian_period', 20)
                    upper = df['high'].rolling(window=period).max().shift(1)
                    lower = df['low'].rolling(window=period).min().shift(1)

                    entries[df['high'] > upper] = 1
                    entries[df['low'] < lower] = -1

            elif b['type'] == 'mean_rev':
                if b['subtype'] == 'rsi':
                    # RSI Reversion
                    rsi = df['rsi']
                    ob = self.config.params.get('rsi_overbought', 70)
                    os = self.config.params.get('rsi_oversold', 30)

                    # Enter Long if RSI < OS
                    entries[rsi < os] = 1
                    # Enter Short if RSI > OB
                    entries[rsi > ob] = -1

                elif b['subtype'] == 'bollinger':
                    # Mean Reversion: Price touches lower band -> Buy?
                    lower = df['bb_lower']
                    upper = df['bb_upper']

                    entries[df['low'] < lower] = 1
                    entries[df['high'] > upper] = -1

        # Apply Filters (mask entries)
        for b in self.config.blocks:
            if b['type'] == 'filter':
                if b['subtype'] == 'adx':
                    thresh = self.config.params.get('adx_threshold', 25)
                    mask = df['adx'] > thresh
                    # If filter fails, zero out entries
                    entries[~mask] = 0
                elif b['subtype'] == 'long_only':
                    entries[entries == -1] = 0

        return entries

    def _apply_risk_overlay(self, df: pd.DataFrame, entries: pd.Series) -> pd.Series:
        # Iterate to handle stateful exits
        positions = pd.Series(0, index=df.index)
        current_pos = 0
        entry_price = 0.0
        bars_in_trade = 0
        highest_high = 0.0 # for trailing
        lowest_low = 0.0

        # Get Exit Params
        exit_block = next((b for b in self.config.blocks if b['type'] == 'exit'), None)
        max_bars = self.config.params.get('max_bars', 0)
        atr_mult = self.config.params.get('stop_atr_mult', 0)
        trail_pct = self.config.params.get('trail_percent', 0)

        # Pre-calc ATR if needed
        atr_series = df['atr'] if 'atr' in df else pd.Series(0, index=df.index)

        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        entry_vals = entries.values
        atr_vals = atr_series.values

        n = len(df)
        pos_arr = np.zeros(n, dtype=int)

        for i in range(1, n):
            # Check Exit first
            if current_pos != 0:
                bars_in_trade += 1
                exit_signal = False

                # Time Stop
                if max_bars > 0 and bars_in_trade >= max_bars:
                    exit_signal = True

                # ATR Stop
                if not exit_signal and atr_mult > 0:
                    # Initial Stop based on Entry Price?
                    # Usually fixed at entry.
                    # Or trailing?
                    # Let's assume Fixed Stop Loss at Entry
                    stop_dist = atr_vals[i-bars_in_trade] * atr_mult # ATR at entry
                    if current_pos == 1:
                        if lows[i] < (entry_price - stop_dist):
                            exit_signal = True
                    else:
                        if highs[i] > (entry_price + stop_dist):
                            exit_signal = True

                # Trailing Stop
                if not exit_signal and trail_pct > 0:
                    if current_pos == 1:
                        highest_high = max(highest_high, highs[i])
                        if lows[i] < highest_high * (1 - trail_pct):
                            exit_signal = True
                    else:
                        lowest_low = min(lowest_low, lows[i])
                        if highs[i] > lowest_low * (1 + trail_pct):
                            exit_signal = True

                if exit_signal:
                    current_pos = 0
                    bars_in_trade = 0

            # Check Entry (only if flat? or reversal?)
            # Usually flat.
            if current_pos == 0:
                if entry_vals[i] != 0:
                    current_pos = int(entry_vals[i])
                    entry_price = closes[i] # Assume filled at Close? Or Next Open?
                    # "Execution: next-bar open".
                    # Here we generate TARGET POSITION for the day.
                    # If we signal today, we enter tomorrow open.
                    # But for risk overlay, we need to know if we are IN trade.
                    # If pos_arr[i] = 1, it means we WANT to be long.
                    # The Backtest Engine will execute this at Open[i+1].

                    bars_in_trade = 0
                    highest_high = highs[i]
                    lowest_low = lows[i]

            # Store State
            pos_arr[i] = current_pos

        return pd.Series(pos_arr, index=df.index)
