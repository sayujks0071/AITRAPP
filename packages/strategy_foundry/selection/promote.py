"""Promotion Logic"""
from packages.strategy_foundry.selection.ranker import ChampionStore

class Promoter:
    def __init__(self):
        self.store = ChampionStore()

    def check_promotion(self, challenger_metrics: dict, challenger_cand: dict) -> bool:
        current = self.store.load_current()
        if not current:
            return True

        curr_score = current["metrics"].get("score", 0)
        chall_score = challenger_metrics.get("score", 0)

        # Rule: Beat score by 10%
        if chall_score > curr_score * 1.10:
            return True

        # Rule: Reduce DD by 5% absolute
        curr_dd = current["metrics"].get("max_drawdown", 1.0)
        chall_dd = challenger_metrics.get("max_drawdown", 1.0)

        if curr_dd - chall_dd > 0.05:
            # But Sharpe must not degrade meaningfully (e.g. > 10% drop)
            curr_sharpe = current["metrics"].get("sharpe", 0)
            chall_sharpe = challenger_metrics.get("sharpe", 0)
            if chall_sharpe >= curr_sharpe * 0.9:
                return True

        return False
