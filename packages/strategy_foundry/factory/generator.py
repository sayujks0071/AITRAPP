import random
import hashlib
import json
from typing import List
from .grammar import StrategyCandidate

class StrategyGenerator:
    def __init__(self):
        pass

    def generate(self, n: int = 50) -> List[StrategyCandidate]:
        candidates = []
        seen_hashes = set()

        while len(candidates) < n:
            cand = self._create_random()
            if cand.id not in seen_hashes:
                candidates.append(cand)
                seen_hashes.add(cand.id)

        return candidates

    def _create_random(self) -> StrategyCandidate:
        blocks = []

        # 1. Entry (Pick 1-2)
        entry_types = ['entry_ema_cross', 'entry_rsi_oversold', 'entry_supertrend', 'entry_breakout']
        num_entries = random.choice([1, 2])
        chosen_entries = random.sample(entry_types, num_entries)

        for et in chosen_entries:
            if et == 'entry_ema_cross':
                blocks.append({
                    'type': et,
                    'params': {'fast': random.choice([10, 20]), 'slow': random.choice([50, 200])}
                })
            elif et == 'entry_rsi_oversold':
                blocks.append({
                    'type': et,
                    'params': {'threshold': random.choice([30, 40])}
                })
            elif et == 'entry_supertrend':
                blocks.append({'type': et, 'params': {}})
            elif et == 'entry_breakout':
                blocks.append({'type': et, 'params': {}})

        # 2. Exit (Pick 1)
        exit_types = ['exit_rsi_overbought', 'exit_supertrend']
        et = random.choice(exit_types)
        if et == 'exit_rsi_overbought':
            blocks.append({
                'type': et,
                'params': {'threshold': random.choice([60, 70, 80])}
            })
        elif et == 'exit_supertrend':
            blocks.append({'type': et, 'params': {}})

        # 3. Filter (Optional)
        if random.random() < 0.5:
             filter_types = ['filter_adx', 'filter_regime']
             ft = random.choice(filter_types)
             if ft == 'filter_adx':
                 blocks.append({'type': ft, 'params': {'threshold': random.choice([20, 25])}})
             elif ft == 'filter_regime':
                 blocks.append({'type': ft, 'params': {}})

        # 4. Risk Params
        params = {
            'stop_atr_mult': random.choice([2.0, 3.0, 4.0]),
            'trailing_stop_atr_mult': random.choice([0.0, 2.0, 3.0]),
            'max_bars': random.choice([0, 5, 10, 20])
        }

        # ID
        s = json.dumps({'blocks': blocks, 'params': params}, sort_keys=True)
        sid = hashlib.sha256(s.encode()).hexdigest()

        return StrategyCandidate(id=sid, blocks=blocks, params=params)
