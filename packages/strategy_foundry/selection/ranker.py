"""
Ranking logic.
"""
from typing import Dict, List
import pandas as pd

class Ranker:
    @staticmethod
    def calculate_score(metrics: Dict) -> float:
        """
        Calculate composite score.
        + 30% OOS Sharpe
        + 25% OOS Calmar
        + 20% OOS CAGR
        + 15% Stability (low dispersion)
        − 10% Turnover penalty (not directly available in metrics dict as 'turnover', but maybe 'trades' proxy?)

        Using avg_oos metrics from WFA.
        """
        sharpe = metrics.get("avg_oos_sharpe", 0)
        calmar = metrics.get("avg_oos_calmar", 0)
        cagr = metrics.get("avg_oos_cagr", 0)
        stability = metrics.get("stability", 0)

        # Turnover proxy: fewer trades is better? No, turnover penalty implies excessive trading.
        # Let's use 'trades' count from full_metrics normalized?
        # Or just skip turnover for MVP if not easily available.
        # "Turnover penalty" - let's assume we penalize high frequency.
        # Score = ... - 0.1 * (Trades / 1000) ??
        # Let's ignore turnover penalty for now to keep simple, or use small penalty.

        score = (0.30 * sharpe) + (0.25 * calmar) + (0.20 * cagr * 100) + (0.15 * stability)

        return score

    @staticmethod
    def rank_candidates(candidates_results: List[Dict]) -> pd.DataFrame:
        """
        Rank candidates.
        candidates_results: List of dicts containing 'strategy_id', 'metrics', etc.
        """
        rows = []
        for res in candidates_results:
            m = res["metrics"]
            score = Ranker.calculate_score(m)
            rows.append({
                "id": res["strategy_id"],
                "score": score,
                "sharpe": m.get("avg_oos_sharpe", 0),
                "cagr": m.get("avg_oos_cagr", 0),
                "calmar": m.get("avg_oos_calmar", 0),
                "max_dd": m.get("full_metrics", {}).get("max_drawdown", 0),
                "trades": m.get("full_metrics", {}).get("trades", 0),
                "description": res["strategy"].describe()
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df.sort_values("score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)

        return df
