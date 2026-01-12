from typing import Dict, Any, List
import pandas as pd
import json
import os
import glob

RESULTS_DIR = "packages/strategy_foundry/results/runs"
CHAMPIONS_DIR = "packages/strategy_foundry/results/champions"

class Ranker:
    def rank(self, candidates: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Rank candidates based on composite score.
        candidates: List of dicts with 'stats' and 'id'.
        """
        rows = []
        for c in candidates:
            stats = c.get('stats', {})
            # Score Calculation
            # 30% Sharpe, 25% Calmar, 20% CAGR, 15% Stability (not calc yet), -10% Turnover?
            # We need normalized values for robust scoring, or raw values with weights.
            # Let's use raw values for simplicity initially, or clipped.

            sharpe = stats.get('avg_sharpe', 0)
            calmar = stats.get('avg_calmar', 0)
            cagr = stats.get('avg_cagr', 0)

            # Clip outlier Calmar
            calmar = min(calmar, 10.0)

            # Simple weighted sum
            score = (0.3 * sharpe) + (0.25 * calmar) + (0.2 * cagr)
            # Ignoring turnover/stability for now in MVP

            row = c.copy()
            row.update(stats)
            row['score'] = score
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values('score', ascending=False)

        return df

class ChampionStore:
    def get_current_champion(self, symbol: str) -> Dict[str, Any]:
        path = os.path.join(CHAMPIONS_DIR, f"current_{symbol}.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return None

    def promote(self, candidate: Dict[str, Any], symbol: str):
        os.makedirs(CHAMPIONS_DIR, exist_ok=True)
        # Save Current
        path = os.path.join(CHAMPIONS_DIR, f"current_{symbol}.json")
        with open(path, 'w') as f:
            json.dump(candidate, f, indent=2)

        # Archive with timestamp
        ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        path_arc = os.path.join(CHAMPIONS_DIR, f"{ts}_{candidate['id']}_{symbol}.json")
        with open(path_arc, 'w') as f:
            json.dump(candidate, f, indent=2)

def check_promotion(current: Dict[str, Any], challenger: Dict[str, Any]) -> bool:
    if not current:
        return True

    score_curr = current.get('score', 0)
    score_chal = challenger.get('score', 0)

    # +10% score improvement
    if score_chal > score_curr * 1.10:
        return True

    # OR Lower MaxDD materially? (Need DD stats in candidate dict)
    # Implementing simple score check first.

    return False
