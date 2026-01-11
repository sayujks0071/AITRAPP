"""Ranker"""
import pandas as pd
from typing import List, Dict

class Ranker:
    def __init__(self):
        pass

    def rank(self, results: List[Dict]) -> pd.DataFrame:
        """
        Rank candidates based on OOS metrics.
        score = 0.25*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability
        """
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Normalize metrics
        # Simple MinMax or Z-score?
        # Let's just use raw weighted sum with some scaling

        df["score"] = (
            0.25 * df["sharpe"].clip(-2, 5) +
            0.25 * (df["calmar"].clip(0, 5)) +
            0.20 * (df["cagr"].clip(-0.5, 2.0) * 2) + # weight cagr similar to others
            0.15 * df["profit_factor"].clip(0, 3)
        )

        return df.sort_values("score", ascending=False)
