from typing import Dict

def should_promote(challenger: Dict, incumbent: Dict) -> bool:
    """
    Promotion rule:
    New must exceed current score by >= 10% OR lower MaxDD by >= 5% absolute (while maintaining positive score).
    """
    if not incumbent:
        return True

    c_score = challenger.get("score", 0)
    i_score = incumbent.get("score", 0)

    if c_score > i_score * 1.10:
        return True

    # Lower MaxDD check
    # MaxDD is negative number usually e.g. -0.20
    # Lower means "closer to 0" or "more negative"?
    # Usually "Lower MaxDD" means smaller magnitude.
    # So if challenger -0.10 and incumbent -0.20.

    c_dd = abs(challenger.get("max_dd", 1.0))
    i_dd = abs(incumbent.get("max_dd", 1.0))

    if c_dd < (i_dd - 0.05) and c_score > i_score * 0.9: # Accept slightly lower score for much better risk
        return True

    return False
