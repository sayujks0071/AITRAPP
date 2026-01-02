import numpy as np
from typing import Dict, Any, List

class StrategyRanker:
    """Ranks strategies based on walk-forward evaluation metrics"""

    def calculate_score(self, evaluation: Dict[str, Any]) -> float:
        if "error" in evaluation:
            return -999.0

        folds = evaluation["folds"]
        if not folds:
            return 0.0

        avg_sharpe = evaluation["avg_sharpe"]
        avg_dd = evaluation["avg_max_drawdown"]
        sharpe_std = evaluation["sharpe_std"]

        avg_cagr = np.mean([m["cagr"] for m in folds])

        # Calmar Ratio Proxy
        if avg_dd > 0.01:
            calmar = avg_cagr / avg_dd
        else:
            calmar = 0.0 if avg_cagr <= 0 else 5.0 # Cap

        # Stability Score (Higher is better)
        stability = 1.0 / (1.0 + sharpe_std)

        # Score Composition
        # Sharpe: Target > 1.0. Range usually -1 to 3.
        # Calmar: Target > 2.0. Range 0 to 10.
        # CAGR: Target > 0.2. Range -0.5 to 1.0+

        # Normalize roughly
        s_sharpe = max(min(avg_sharpe, 3.0), -3.0)
        s_calmar = max(min(calmar, 5.0), 0.0)
        s_cagr = max(min(avg_cagr, 2.0), -1.0)

        score = (0.3 * s_sharpe) + (0.3 * s_calmar) + (0.2 * s_cagr) + (0.2 * stability)

        # Penalty for low trades (overfitting small sample)
        total_trades = evaluation["total_trades"]
        if total_trades < 20: # Arbitrary threshold for 4 folds
            score *= 0.5

        return float(score)

    def rank(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank candidates.
        Candidates list must contain 'evaluation' key.
        """
        for c in candidates:
            c["score"] = self.calculate_score(c.get("evaluation", {}))

        return sorted(candidates, key=lambda x: x["score"], reverse=True)
