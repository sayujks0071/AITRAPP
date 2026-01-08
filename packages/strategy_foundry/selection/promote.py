from typing import Dict, Any, Optional

def should_promote(challenger: Dict[str, Any], champion: Optional[Dict[str, Any]]) -> bool:
    """
    Check if challenger should replace champion.
    """
    if not champion:
        return True

    # Scores
    c_score = champion.get('score', 0)
    ch_score = challenger.get('score', 0)

    # Check score improvement (10%)
    if ch_score > c_score * 1.10:
        return True

    # Check MaxDD improvement (Materially lower, e.g. 20% less DD)
    # Note: MaxDD is a positive number (0.20 = 20%)
    c_dd = champion.get('metrics', {}).get('max_dd', 1.0)
    ch_dd = challenger.get('metrics', {}).get('max_dd', 1.0)

    if ch_dd < c_dd * 0.8:
        # But must not degrade Return too much?
        # Let's say if Score is at least 90% of champion
        if ch_score > c_score * 0.90:
            return True

    return False
