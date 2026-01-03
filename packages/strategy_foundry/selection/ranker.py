from typing import List, Dict
from packages.strategy_foundry.factory.generator import StrategyCandidate
from packages.strategy_foundry.backtest.metrics import compute_metrics

class Ranker:
    def __init__(self):
        pass

    def rank(self, results: List[Dict]) -> List[Dict]:
        """
        Rank candidates based on blended score.
        Results list of dicts: {candidate, metrics_oos_5m, metrics_oos_15m, metrics_1d}
        """
        # Score = Sharpe * 0.4 + NetReturn * 0.2 + (1/MaxDD) * 0.2 ...

        ranked = []
        for res in results:
            score = 0

            # Simple scoring
            m5 = res.get('metrics_oos_5m', {})
            m15 = res.get('metrics_oos_15m', {})

            s5 = m5.get('sharpe', 0)
            s15 = m15.get('sharpe', 0)

            # Blended Score
            # Prefer 15m stability
            blended_sharpe = (s15 * 0.6) + (s5 * 0.4)

            score = blended_sharpe

            # Penalize MaxDD
            dd = max(m5.get('max_dd', 0), m15.get('max_dd', 0))
            if dd > 0.3: # > 30% drawdown
                score -= 10

            # Penalize low trades
            trades = m5.get('trades', 0) + m15.get('trades', 0)
            if trades < 20:
                score -= 5

            res['score'] = score
            ranked.append(res)

        ranked.sort(key=lambda x: x['score'], reverse=True)
        return ranked
