"""
Ranking logic for strategies.
"""
from typing import List, Dict, Any
import pandas as pd

def rank_candidates(candidates: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Rank candidates based on score.
    candidate dict must contain: id, metrics, wf_metrics, etc.
    """
    if not candidates:
        return pd.DataFrame()

    rows = []
    for c in candidates:
        m = c["metrics"]
        wf = c["wf_metrics"]

        # Calculate Score
        # 25% Sharpe, 25% Calmar, 20% CAGR, 15% Stability, 10% Low Turnover, 5% Sanity

        sharpe_score = min(m["sharpe"] / 2.0, 1.0) # Cap at 2.0
        calmar_score = min(m["calmar"] / 3.0, 1.0) # Cap at 3.0
        cagr_score = min(m["cagr"] / 0.5, 1.0) # Cap at 50%

        # Stability: 1.0 if 4/4 folds positive, 0.75 if 3/4, etc.
        stability = wf["consistency"] / wf["n_folds"] if wf["n_folds"] > 0 else 0

        # Turnover score: Higher trades = lower score? Or higher profit/trade?
        # Let's use profit factor as proxy for quality per trade
        pf_score = min((m["profit_factor"] - 1.0) / 1.0, 1.0) # 2.0 PF = max score

        score = (0.25 * sharpe_score) + \
                (0.25 * calmar_score) + \
                (0.20 * cagr_score) + \
                (0.15 * stability) + \
                (0.15 * pf_score)

        row = {
            "id": c["id"],
            "score": score,
            "sharpe": m["sharpe"],
            "calmar": m["calmar"],
            "cagr": m["cagr"],
            "max_dd": m["max_dd"],
            "trades": m["trades"],
            "consistency": f"{wf['consistency']}/{wf['n_folds']}",
            "strategy": c["strategy_obj"]
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.sort_values("score", ascending=False)
