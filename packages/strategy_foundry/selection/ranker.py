from typing import Dict, Any, List
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def rank_candidates(candidates: List[StrategyCandidate]) -> List[StrategyCandidate]:
    """
    Rank candidates based on composite score.
    Score = 0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*TurnoverPenalty
    """
    scored = []

    for c in candidates:
        m = c.metrics
        if not m: continue

        # Normalize/Clamp metrics for scoring
        sharpe = max(0, min(3, m.get("avg_sharpe", 0)))
        calmar = max(0, min(5, m.get("avg_cagr", 0) / abs(m.get("avg_max_dd", -0.01))))
        cagr = max(0, min(1.0, m.get("avg_cagr", 0)))
        stability = max(0, min(1, m.get("stability", 0)))

        score = (0.30 * sharpe) + \
                (0.25 * calmar) + \
                (0.20 * cagr) + \
                (0.15 * stability)

        # Add score to metrics for reference
        c.metrics["score"] = score
        scored.append(c)

    # Sort descending
    scored.sort(key=lambda x: x.metrics["score"], reverse=True)
    return scored
