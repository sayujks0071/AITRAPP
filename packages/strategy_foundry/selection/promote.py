from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.factory.grammar import StrategyConfig
import numpy as np

class Promoter:
    def __init__(self, instrument="NIFTY"):
        self.store = ChampionStore(instrument)

    def check_and_promote(self, challenger_row: dict) -> bool:
        """
        challenger_row: dict from Ranker (strategy_obj, score, metrics_list, max_dd)
        """
        current = self.store.load_current_champion()

        challenger_strat = challenger_row['strategy_obj']
        challenger_score = challenger_row['score']
        challenger_metrics = challenger_row['metrics_list']

        # Gates
        # 1. Live Eligible?
        # OOS Sharpe >= 1.0
        avg_sharpe = np.mean([m.get('sharpe', 0) for m in challenger_metrics])
        if avg_sharpe < 1.0:
            return False

        # MaxDD <= 25%
        # max_dd in metrics is negative (e.g. -0.10).
        worst_dd = np.min([m.get('max_dd', 0) for m in challenger_metrics])
        if abs(worst_dd) > 0.25:
             return False

        # >= 3 positive OOS folds
        # Or simpler: positive CAGR in X folds?
        # Requirement: ">= 3 positive OOS folds"
        # Since we use e.g. 3 folds, implies all positive? Or if >3 folds?
        pos_folds = sum(1 for m in challenger_metrics if m.get('total_return', 0) > 0)
        # If FAST_MODE (2 folds), we can't have 3.
        # "FAST_MODE doesn’t promote" is handled by runner usually, but logic here:
        if len(challenger_metrics) < 3:
             # Can't satisfy condition
             # Unless we relax for FAST_MODE?
             # User said: "FAST_MODE doesn’t promote" in 6).
             # So if folds < 3, return False.
             if len(challenger_metrics) < 3:
                 return False

        if pos_folds < 3:
            return False

        if not current:
            # No champion, promote immediately
            self.store.save_new_champion(challenger_strat, challenger_score, challenger_metrics)
            return True

        # Compare with current
        current_score = current['score']
        current_metrics = current['metrics']
        current_dd = np.min([m.get('max_dd', 0) for m in current_metrics])

        # Rule: Exceed score by >= 10% OR lower MaxDD materially (5% absolute?)
        # "materially" - let's say 5% better (e.g. -20% vs -25%)

        score_improv = (challenger_score - current_score) / abs(current_score) if current_score != 0 else 0.11

        dd_improv = abs(current_dd) - abs(worst_dd) # Positive if challenger is better (lower absolute DD)

        promote = False
        if score_improv >= 0.10:
            promote = True
        elif dd_improv >= 0.05: # e.g. 0.25 - 0.20 = 0.05
            promote = True

        if promote:
            self.store.save_new_champion(challenger_strat, challenger_score, challenger_metrics)
            return True

        return False
