import pandas as pd
from typing import Dict, Any

class Ranker:
    def rank(self, results: pd.DataFrame) -> pd.DataFrame:
        """
        Rank candidates based on composite score.
        results DataFrame should have columns matching metric names.
        """
        # Composite Score Weights
        # 30% Sharpe, 25% Calmar, 20% CAGR, 15% Stability (inv), 10% Turnover (inv)

        df = results.copy()

        # Normalize
        # Handle zeros/NaNs
        df = df.fillna(0)

        # Stability: Lower is better. Invert.
        # Turnover: Lower is better. Invert.

        # Score =
        # 0.3 * norm(Sharpe) +
        # 0.25 * norm(Calmar) +
        # 0.2 * norm(CAGR) +
        # 0.15 * (1 - norm(Stability)) -
        # 0.1 * norm(Turnover)

        # Simple Rank Sum logic might be robust enough
        df["score"] = (
            0.3 * df["sharpe"] +
            0.25 * df["calmar"] +
            0.2 * df["cagr"]
        )

        # Penalize High DD
        df.loc[df["max_dd"] > 0.35, "score"] *= 0.5

        # Penalize Low Trades
        df.loc[df["total_trades"] < 10, "score"] = -1

        return df.sort_values("score", ascending=False)
