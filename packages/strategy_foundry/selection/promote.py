import os
import json
import logging
from datetime import datetime
from packages.strategy_foundry.factory.grammar import StrategyConfig

logger = logging.getLogger(__name__)

class Promoter:
    def __init__(self, instrument: str, timeframe: str):
        self.instrument = instrument
        self.timeframe = timeframe
        self.champions_dir = "packages/strategy_foundry/results/champions"
        os.makedirs(self.champions_dir, exist_ok=True)

        # Current champion file: e.g. NIFTY_blended_current.json
        self.current_path = os.path.join(self.champions_dir, f"{instrument}_{timeframe}_current.json")

    def check_and_promote(self, candidate_row: dict) -> bool:
        """
        Check if candidate beats current champion.
        candidate_row: contains 'score', 'sharpe', 'max_dd', 'strategy_config'
        """
        new_score = candidate_row['score']
        new_sharpe = candidate_row.get('sharpe', 0) # Avg sharpe
        new_dd = candidate_row.get('avg_max_dd', candidate_row.get('max_dd', 1.0))

        # Load current
        current = self._load_current()

        promote = False
        reason = ""

        if not current:
            promote = True
            reason = "No existing champion"
        else:
            curr_score = current.get('score', 0)
            curr_dd = current.get('max_dd', 1.0)

            # Rule 1: Beat Score by 10%
            if new_score >= curr_score * 1.10:
                promote = True
                reason = f"Score improved > 10% ({curr_score:.2f} -> {new_score:.2f})"

            # Rule 2: Reduce MaxDD by 5% absolute (e.g. 0.20 -> 0.15)
            # while not degrading Sharpe meaningfully (say, not < 90% of current)
            elif (curr_dd - new_dd) >= 0.05:
                curr_sharpe = current.get('sharpe', 0)
                if new_sharpe >= curr_sharpe * 0.9:
                    promote = True
                    reason = f"DD reduced by > 5% ({curr_dd:.2f} -> {new_dd:.2f})"

        if promote:
            logger.info(f"Promoting new champion for {self.instrument} {self.timeframe}: {reason}")
            self._save_champion(candidate_row)
            return True

        return False

    def _load_current(self):
        if not os.path.exists(self.current_path):
            return None
        try:
            with open(self.current_path, 'r') as f:
                return json.load(f)
        except:
            return None

    def _save_champion(self, data: dict):
        # Add timestamp
        data['promoted_at'] = datetime.now().isoformat()

        # Save as current
        with open(self.current_path, 'w') as f:
            json.dump(data, f, indent=2)

        # Versioned
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sid = data.get('strategy_id', 'unknown')
        v_path = os.path.join(self.champions_dir, f"{self.instrument}_{self.timeframe}_{ts}_{sid}.json")
        with open(v_path, 'w') as f:
            json.dump(data, f, indent=2)
