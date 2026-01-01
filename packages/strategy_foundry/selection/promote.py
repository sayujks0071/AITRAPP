"""Promotion Gates"""
from typing import Dict, Any, Tuple, List

def can_promote(candidate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if candidate can be promoted to Live.
    Returns (Passed, Reasons)
    """
    reasons = []
    passed = True

    m = candidate.get("metrics", {})
    wf = candidate.get("walkforward", {})

    # Gates
    if m.get("sharpe", 0) < 1.0:
        passed = False
        reasons.append(f"Sharpe {m.get('sharpe'):.2f} < 1.0")

    if m.get("max_dd", 1.0) > 0.25:
        passed = False
        reasons.append(f"MaxDD {m.get('max_dd'):.2f} > 0.25")

    if wf.get("positive_folds", 0) < 3:
        passed = False
        reasons.append(f"Positive Folds {wf.get('positive_folds')} < 3")

    return passed, reasons
