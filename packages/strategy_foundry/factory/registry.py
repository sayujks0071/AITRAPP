import json
import os
from packages.strategy_foundry.factory.grammar import StrategyConfig, Rule

class CandidateRegistry:
    @staticmethod
    def save_candidates(candidates: list[StrategyConfig], filepath: str):
        """Saves candidates to JSON file."""
        data = [c.to_dict() for c in candidates]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_candidates(filepath: str) -> list[StrategyConfig]:
        """Loads candidates from JSON file."""
        if not os.path.exists(filepath):
            return []

        with open(filepath, 'r') as f:
            data = json.load(f)

        candidates = []
        for d in data:
            # Reconstruct objects
            # Needed: parsing dictionaries back to Rule objects
            entry_rules = [Rule(**r) for r in d['entry_rules']]
            exit_rules = [Rule(**r) for r in d['exit_rules']]

            c = StrategyConfig(
                strategy_id=d['strategy_id'],
                entry_rules=entry_rules,
                exit_rules=exit_rules,
                stop_loss_atr=d['stop_loss_atr'],
                take_profit_atr=d['take_profit_atr'],
                max_bars_hold=d['max_bars_hold']
            )
            candidates.append(c)
        return candidates
