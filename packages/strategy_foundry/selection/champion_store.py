import json
import os
import shutil
from datetime import datetime
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.factory.registry import CandidateRegistry

CHAMPIONS_DIR = "packages/strategy_foundry/results/champions"
CURRENT_CHAMPION_FILE = os.path.join(CHAMPIONS_DIR, "current.json")

class ChampionStore:
    def __init__(self, instrument="NIFTY"):
        self.instrument = instrument
        self.current_file = CURRENT_CHAMPION_FILE.replace(".json", f"_{instrument}.json")
        os.makedirs(CHAMPIONS_DIR, exist_ok=True)

    def load_current_champion(self) -> dict:
        """Returns dict with 'strategy': StrategyConfig, 'score': float, 'metrics': list"""
        if not os.path.exists(self.current_file):
            return None

        with open(self.current_file, 'r') as f:
            data = json.load(f)

        # Reconstruct StrategyConfig
        # Similar logic to Registry
        # (Copy-paste logic or use Registry if generic)
        # Assuming data structure: { 'strategy': {...}, 'score': ..., 'metrics': ... }

        # Helper to hydrate strategy
        strat_dict = data['strategy']
        # We can use CandidateRegistry logic if we adapt it.
        # Let's just inline for now or make Registry more granular.

        # Using Registry to load temp file is safer
        # But here we have dict.
        from packages.strategy_foundry.factory.grammar import Rule
        entry_rules = [Rule(**r) for r in strat_dict['entry_rules']]
        exit_rules = [Rule(**r) for r in strat_dict['exit_rules']]

        strat = StrategyConfig(
            strategy_id=strat_dict['strategy_id'],
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            stop_loss_atr=strat_dict['stop_loss_atr'],
            take_profit_atr=strat_dict['take_profit_atr'],
            max_bars_hold=strat_dict['max_bars_hold']
        )

        return {
            "strategy": strat,
            "score": data.get('score', 0.0),
            "metrics": data.get('metrics', [])
        }

    def save_new_champion(self, strategy: StrategyConfig, score: float, metrics: list):
        # 1. Archive current
        if os.path.exists(self.current_file):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Load old id to append
            try:
                with open(self.current_file) as f:
                    old_data = json.load(f)
                    old_id = old_data['strategy']['strategy_id']
            except:
                old_id = "unknown"

            archive_name = f"{ts}_{old_id}_{self.instrument}.json"
            shutil.copy(self.current_file, os.path.join(CHAMPIONS_DIR, archive_name))

        # 2. Save new
        data = {
            "strategy": strategy.to_dict(),
            "score": score,
            "metrics": metrics,
            "promoted_at": datetime.now().isoformat()
        }
        with open(self.current_file, 'w') as f:
            json.dump(data, f, indent=2)

