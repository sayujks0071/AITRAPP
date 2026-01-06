import pandas as pd
import numpy as np
import json
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class StrategyCandidate:
    id: str
    blocks: List[Dict[str, Any]]
    params: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "blocks": self.blocks,
            "params": self.params
        }, sort_keys=True)

    @staticmethod
    def from_json(json_str: str) -> 'StrategyCandidate':
        data = json.loads(json_str)
        return StrategyCandidate(id=data["id"], blocks=data["blocks"], params=data["params"])

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generates target positions (1 for Long, 0 for Flat).
        Shorts (-1) not supported in this version.
        """
        # 1. Calculate indicators if not present (assumed passed df has them or we compute)
        # For safety, we assume df has all base indicators from core_indicators adapter

        # 2. Evaluate Blocks
        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)
        filters = pd.Series(True, index=df.index)

        # Parse blocks
        for block in self.blocks:
            btype = block['type']
            params = block['params']

            if btype == 'entry_ema_cross':
                # Fast crosses above Slow
                fast = df[f"ema_{params['fast']}"]
                slow = df[f"ema_{params['slow']}"]
                # Vectorized cross
                cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
                entries = entries | cross

            elif btype == 'entry_rsi_oversold':
                entries = entries | (df['rsi_14'] < params['threshold'])

            elif btype == 'entry_supertrend':
                # Enter if Supertrend is bullish (1)
                entries = entries | (df['supertrend_dir'] == 1) & (df['supertrend_dir'].shift(1) == -1)

            elif btype == 'entry_breakout':
                # Close > Donchian Upper previous
                entries = entries | (df['close'] > df['donchian_upper_20'].shift(1))

            elif btype == 'exit_rsi_overbought':
                exits = exits | (df['rsi_14'] > params['threshold'])

            elif btype == 'exit_supertrend':
                exits = exits | (df['supertrend_dir'] == -1)

            elif btype == 'filter_adx':
                filters = filters & (df['adx_14'] > params['threshold'])

            elif btype == 'filter_regime':
                # e.g. close > ema_200
                filters = filters & (df['close'] > df['ema_200'])

        # 3. Apply Risk (Stops) & State Machine
        # Risk params
        stop_atr_mult = self.params.get('stop_atr_mult', 3.0)
        trailing_stop_atr_mult = self.params.get('trailing_stop_atr_mult', 0.0) # 0 means disabled
        max_bars = self.params.get('max_bars', 0)

        positions = np.zeros(len(df), dtype=int)

        # Arrays for speed
        c = df['close'].values
        h = df['high'].values
        l = df['low'].values
        atr = df['atr_14'].values

        # Boolean arrays
        entry_arr = (entries & filters).values
        exit_arr = exits.values

        # State
        in_position = False
        entry_price = 0.0
        entry_idx = 0
        highest_price = 0.0

        for i in range(1, len(df)):
            if in_position:
                # Check Exits
                # 1. Signal Exit
                if exit_arr[i]:
                    in_position = False
                    positions[i] = 0
                    continue

                # 2. Stop Loss (Fixed ATR from entry)
                sl_price = entry_price - (atr[entry_idx] * stop_atr_mult)
                if l[i] < sl_price:
                    in_position = False
                    positions[i] = 0
                    continue

                # 3. Trailing Stop
                if trailing_stop_atr_mult > 0:
                    highest_price = max(highest_price, h[i])
                    ts_price = highest_price - (atr[i] * trailing_stop_atr_mult)
                    if c[i] < ts_price: # Check against close or low? Standard is usually breaching low, but for daily maybe close? sticking to low for safety
                        if l[i] < ts_price:
                           in_position = False
                           positions[i] = 0
                           continue

                # 4. Time Stop
                if max_bars > 0 and (i - entry_idx) >= max_bars:
                    in_position = False
                    positions[i] = 0
                    continue

                # Still in position
                positions[i] = 1

            else:
                # Check Entry
                if entry_arr[i]:
                    in_position = True
                    positions[i] = 1 # Enter on close (theoretical) or next open.
                    # Note: Backtest engine handles "next open" execution.
                    # Here we just mark "we want to be in position".
                    entry_price = c[i]
                    entry_idx = i
                    highest_price = c[i]

        return pd.Series(positions, index=df.index)

    def rule_summary(self) -> str:
        s = [f"ID: {self.id[:8]}"]
        for b in self.blocks:
            s.append(f"{b['type']}: {b['params']}")
        s.append(f"Risk: {self.params}")
        return "\n".join(s)

