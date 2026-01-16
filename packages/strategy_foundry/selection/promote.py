"""Promotion Logic"""
from typing import Dict, Any

def should_promote(challenger_score: float, current_score: float, challenger_dd: float, current_dd: float) -> bool:
    """
    Promotion Rule:
    1. Score >= 1.10 * Current Score OR
    2. MaxDD significantly better (e.g. half) with similar score
    """
    if challenger_score >= current_score * 1.10:
        return True

    if challenger_dd < current_dd * 0.7 and challenger_score >= current_score * 0.9:
        return True

    return False
