from typing import List, Dict, Any
import pandas as pd

class Ranker:
    def rank_candidates(self, results: List[Dict]) -> pd.DataFrame:
        """
        Rank candidates based on OOS metrics.
        Score = 0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*Turnover
        """
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Normalize
        # Handle division by zero or infinites

        # We assume results contain aggregated OOS metrics
        # 'sharpe', 'calmar', 'cagr', 'stability', 'turnover'

        # Calculate score
        # Clip negative values for scoring?

        df['score'] = (
            0.3 * df['sharpe'].fillna(0) +
            0.25 * df['calmar'].fillna(0) +
            0.2 * df['cagr'].fillna(0) +
            0.15 * df.get('stability', 0) -
            0.1 * df.get('turnover', 0)
        )

        return df.sort_values("score", ascending=False)
