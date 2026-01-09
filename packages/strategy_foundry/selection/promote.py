from packages.strategy_foundry.factory.grammar import StrategyCandidate

def should_promote(challenger: StrategyCandidate, incumbent: StrategyCandidate) -> bool:
    """
    Promotion Logic:
    1. Score improvement >= 10%
    2. OR MaxDD reduction >= 5% (absolute) with Sharpe delta > -0.1
    """
    if not incumbent:
        return True

    c_score = challenger.metrics.get("score", 0)
    i_score = incumbent.metrics.get("score", 0)

    if i_score == 0: return True

    score_imp = (c_score - i_score) / i_score
    if score_imp >= 0.10:
        return True

    c_dd = challenger.metrics.get("avg_max_dd", -1.0)
    i_dd = incumbent.metrics.get("avg_max_dd", -1.0)

    # DD is negative number. Improvement means c_dd > i_dd + 0.05 ?
    # E.g. c_dd = -0.10, i_dd = -0.20. Diff is +0.10.

    if c_dd > (i_dd + 0.05):
        c_sharpe = challenger.metrics.get("avg_sharpe", 0)
        i_sharpe = incumbent.metrics.get("avg_sharpe", 0)
        if (c_sharpe - i_sharpe) > -0.1:
            return True

    return False

def is_live_eligible(candidate: StrategyCandidate, fast_mode: bool = False) -> bool:
    """
    Gating criteria for live publishing.
    """
    if fast_mode:
        return False # Never promote in fast mode? Or just strict?

    m = candidate.metrics
    if m.get("avg_sharpe", 0) < 1.0: return False
    if m.get("avg_max_dd", -1.0) < -0.25: return False # MaxDD > 25%
    if m.get("positive_folds", 0) < 3: return False

    return True
