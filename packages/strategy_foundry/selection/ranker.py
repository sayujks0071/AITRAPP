from typing import Dict, Any

def calculate_score(metrics: Dict[str, Any], stability_std: float) -> float:
    """
    Calculate composite score for a strategy.
    """
    sharpe = metrics.get("sharpe", 0)
    calmar = metrics.get("calmar", 0)
    cagr = metrics.get("cagr", 0)
    trades = metrics.get("trades", 0)

    # Heuristic Scoring
    s_sharpe = sharpe * 30.0
    s_calmar = calmar * 12.5
    s_cagr = cagr * 100.0

    # Stability (Inverse of Sharpe Std Dev)
    # Lower std dev is better.
    # If std is 0 (one fold?), cap it.
    if stability_std < 0.1:
        s_stability = 15.0 # Max points
    else:
        s_stability = (1.0 / stability_std) * 5.0
        s_stability = min(s_stability, 15.0)

    # Turnover Penalty
    # Assume 252 days. Trades per year ~ Trades / (Total Days / 365)
    # If we don't have total days, just use raw trades count for now or assume 5 years.
    # Let's use simple logic: Too many trades is bad?
    # User says "- 10% Turnover penalty".
    # High turnover reduces scalability.
    # Penalty = (Trades / 100) * 10?
    s_turnover_penalty = (trades / 100.0) * 5.0

    score = s_sharpe + s_calmar + s_cagr + s_stability - s_turnover_penalty
    return max(score, 0.0)
