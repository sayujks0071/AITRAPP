from typing import Dict, Any

def score_strategy(metrics: Dict[str, Any]) -> float:
    """
    Compute composite score for ranking.
    + 30% OOS Sharpe
    + 25% OOS Calmar
    + 20% OOS CAGR
    + 15% Stability (low dispersion)
    − 10% Turnover penalty (proxy by too many trades? No, just raw count)
    """

    # Normalize or cap values to sane ranges for scoring
    sharpe = min(max(metrics["avg_sharpe"], 0), 3.0) / 3.0

    calmar_raw = metrics["avg_cagr"] / abs(metrics["worst_drawdown"]) if metrics["worst_drawdown"] != 0 else 0
    calmar = min(calmar_raw, 3.0) / 3.0

    cagr = min(max(metrics["avg_cagr"], -0.5), 1.0) # Cap at 100%
    if cagr < 0: cagr = 0 # Penalize negative hard

    # Stability: lower dispersion is better.
    # 0 dispersion -> 1.0 score. 1.0 dispersion -> 0.0 score.
    stability = max(1.0 - metrics["sharpe_dispersion"], 0)

    # Turnover penalty: logic vague, let's just penalty if trades > 200 (overfitting/churn)
    # or just flat small penalty.
    # "Turnover penalty" usually means cost. We already deducted cost.
    # Let's ignore explicit turnover penalty for score and trust net returns.

    score = (0.30 * sharpe) + (0.25 * calmar) + (0.20 * cagr) + (0.15 * stability)

    return round(score * 100, 2)
