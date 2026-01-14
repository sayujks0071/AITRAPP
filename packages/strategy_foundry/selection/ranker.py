import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_stability(fold_metrics: List[Dict[str, Any]]) -> float:
    """
    Calculate stability score based on variance of Sharpe across folds.
    Returns 0.0 to 1.0 (1.0 = very stable).
    """
    if not fold_metrics or len(fold_metrics) < 2:
        return 0.5

    sharpes = [m.get("sharpe", 0) for m in fold_metrics]
    mean_s = np.mean(sharpes)
    std_s = np.std(sharpes)

    if mean_s <= 0:
        return 0.0

    # Coefficient of variation approach
    cv = std_s / mean_s if mean_s > 0.1 else 1.0

    # Map CV to 0-1. CV=0 -> 1. CV=1 -> 0.
    stability = max(0.0, 1.0 - cv)
    return stability

def calculate_score(metrics: Dict[str, Any], fold_metrics: List[Dict[str, Any]] = None) -> float:
    """
    Calculate blended score for a candidate run.
    """
    sharpe = metrics.get("sharpe", 0)
    max_dd = metrics.get("max_dd", 1.0)
    if max_dd == 0: max_dd = 0.001

    calmar = metrics.get("cagr", 0) / max_dd # Using CAGR for Calmar if available, else total return
    if "cagr" not in metrics:
        calmar = metrics.get("total_return", 0) / max_dd

    ret = metrics.get("total_return", 0)

    stability = calculate_stability(fold_metrics) if fold_metrics else 0.5

    # Turnover bonus (trades per day approx)
    # Lower is better? "Low turnover bonus".
    # But we want enough trades.
    # Let's use Profit Factor as proxy for quality? No, explicit turnover.
    # Just skip detailed turnover calc for now, give flat bonus if "good".
    turnover_score = 0.5
    if metrics.get("trades", 0) < 500: # Not HFT
        turnover_score = 0.8

    # Weights
    # 25% Sharpe (Target 2.0) -> cap at 3.0 -> norm = sharpe/3
    # 25% Calmar (Target 3.0) -> cap at 5.0 -> norm = calmar/5
    # 20% Return (Target 0.5) -> cap at 1.0 -> norm = ret/1
    # 15% Stability (0-1)
    # 10% Turnover (0-1)
    # 5% Sanity (assumed 1 if passed)

    w_sharpe = min(sharpe / 3.0, 1.0) * 25
    w_calmar = min(calmar / 5.0, 1.0) * 25
    w_ret = min(ret / 1.0, 1.0) * 20
    w_stab = stability * 15
    w_turn = turnover_score * 10
    w_sanity = 5 # Passed

    score = w_sharpe + w_calmar + w_ret + w_stab + w_turn + w_sanity
    return score

def rank_candidates(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Rank candidates.
    Results list of dicts: {candidate_id, metrics, fold_metrics, ...}
    """
    rows = []
    for r in results:
        score = calculate_score(r["metrics"], r.get("fold_metrics"))
        row = r.copy()
        row["score"] = score
        # Flatten metrics for display
        for k, v in r["metrics"].items():
            row[f"metric_{k}"] = v
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("score", ascending=False)
    return df
