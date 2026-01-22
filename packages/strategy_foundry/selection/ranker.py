from typing import List, Dict
import pandas as pd

class Ranker:
    """
    Ranks strategies based on metrics.
    """

    @staticmethod
    def calculate_score(metrics: Dict[str, float]) -> float:
        """
        Calculate composite score.
        Weights:
        Sharpe: 25%
        Calmar: 25%
        CAGR: 20% (as decimal, e.g. 0.2)
        Stability: 15% (Not calculated yet, assuming 1.0 for now or passed in metrics)
        Turnover: 10% (Penalty if high? Bonus if low?)

        Let's simplify: Score = Sharpe + (Calmar/2) + (CAGR*5)
        Sharpe 1.0 -> 1.0
        Calmar 2.0 -> 1.0
        CAGR 0.2 -> 1.0
        Total ~ 3.0
        """
        sharpe = metrics.get("sharpe", 0)
        calmar = metrics.get("calmar", 0)
        cagr = metrics.get("cagr", 0)

        # Stability proxy: Profit Factor
        pf = metrics.get("profit_factor", 0)

        # Penalties
        max_dd = metrics.get("max_dd", 100)
        if max_dd > 30: # Hard penalty
            return -1.0

        score = (sharpe * 0.3) + (calmar * 0.2) + (cagr * 2.0) + (pf * 0.1)

        return score

    @staticmethod
    def rank_candidates(candidates_results: List[Dict]) -> List[Dict]:
        """
        Rank candidates.
        Input: List of dicts with 'candidate', 'metrics_5m', 'metrics_15m'.
        """
        scored = []
        for res in candidates_results:
            m5 = res.get("metrics_5m", {})
            m15 = res.get("metrics_15m", {})

            s5 = Ranker.calculate_score(m5)
            s15 = Ranker.calculate_score(m15)

            # Blended Score
            if m5 and m15:
                blended = (0.6 * s15) + (0.4 * s5)
            elif m15:
                blended = s15
            elif m5:
                blended = s5
            else:
                blended = -99.0

            res["score"] = blended
            scored.append(res)

        # Sort descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
