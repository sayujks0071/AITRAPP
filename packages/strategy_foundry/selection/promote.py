from typing import Dict, Any, Tuple

def should_promote(challenger: Dict[str, Any], incumbent: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Determine if challenger should replace incumbent.
    Returns (should_promote, reason)
    """
    if not incumbent:
        return True, "No incumbent"

    c_score = challenger.get("score", 0)
    i_score = incumbent.get("blended_score", 0)

    # 1. Beat score by 10%
    if c_score >= i_score * 1.10:
        return True, f"Score improvement: {c_score:.2f} vs {i_score:.2f}"

    # 2. Reduce MaxDD by 5% absolute
    c_dd = challenger["metrics"].get("max_dd", 1.0)
    i_dd = incumbent["metrics"].get("max_dd", 1.0)

    if c_dd <= (i_dd - 0.05):
        # Check Sharpe degradation
        c_sharpe = challenger["metrics"].get("sharpe", 0)
        i_sharpe = incumbent["metrics"].get("sharpe", 0)

        # If incumbent sharpe is very low, this check is trivial
        # If incumbent sharpe is high, we want to maintain it
        if i_sharpe > 0.5:
            if c_sharpe >= i_sharpe * 0.9:
                return True, f"MaxDD reduction: {c_dd:.1%} vs {i_dd:.1%} with stable Sharpe"
        else:
            # If incumbent sharpe was bad, we take the DD improvement
            return True, f"MaxDD reduction: {c_dd:.1%} vs {i_dd:.1%}"

    return False, "Insufficient improvement"
