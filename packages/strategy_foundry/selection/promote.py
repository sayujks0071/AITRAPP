from typing import Dict
from .ranker import score_candidate
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def should_promote(
    challenger: StrategyCandidate,
    challenger_metrics: Dict,
    current_metrics: Dict = None
) -> bool:
    """
    Promotion rule:
    - If no current, yes.
    - If new score > current score * 1.10 (10% improvement)
    - OR if MaxDD is materially lower (e.g. half) with similar returns?
    """
    challenger_score = score_candidate(challenger_metrics)

    if not current_metrics:
        # Check absolute gates
        if challenger_metrics.get('sharpe', 0) < 0.5: return False
        if abs(challenger_metrics.get('max_drawdown', 0)) > 0.40: return False
        return True

    current_score = score_candidate(current_metrics)

    # 10% improvement
    if challenger_score > current_score * 1.10:
        return True

    # Lower MaxDD
    c_dd = abs(challenger_metrics.get('max_drawdown', 1))
    o_dd = abs(current_metrics.get('max_drawdown', 1))

    if c_dd < o_dd * 0.7 and challenger_score > current_score * 0.9:
        return True

    return False
