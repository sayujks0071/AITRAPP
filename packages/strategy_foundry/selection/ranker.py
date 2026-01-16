"""Ranking Logic"""
from typing import Dict, Any

def calculate_score(metrics: Dict[str, Any]) -> float:
    """
    Composite Score Calculation:
    + 30% OOS Sharpe
    + 25% OOS Calmar
    + 20% OOS CAGR
    + 15% Stability (proxy via sharpe/vol?) - Simplified to positive folds ratio
    - 10% Turnover penalty (not avail, ignored)
    """
    sharpe = metrics.get('oos_sharpe', 0)
    # Calmar can be infinite, cap it
    calmar = metrics.get('oos_cagr', 0) / abs(metrics.get('oos_max_dd', 1.0) + 0.001)
    calmar = min(calmar, 5.0)

    cagr = metrics.get('oos_cagr', 0)

    folds_score = metrics.get('positive_folds', 0) / max(1, metrics.get('total_folds', 1))

    score = (0.30 * sharpe) + (0.25 * calmar) + (0.20 * cagr) + (0.15 * folds_score)
    return float(score)
