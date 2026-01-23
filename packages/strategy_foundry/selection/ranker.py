from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

class Ranker:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        # Weights
        self.w_sharpe = 0.25
        self.w_calmar = 0.25
        self.w_cagr = 0.20
        self.w_stability = 0.15
        self.w_turnover = 0.10
        self.w_sanity = 0.05

        # Constraints
        self.min_trades = self.config.get("min_trades_5m", 80) # Default for 5m
        self.max_dd = self.config.get("max_dd_pct", 30.0)
        self.min_pf = self.config.get("min_profit_factor", 1.1)
        self.min_folds = self.config.get("min_positive_folds", 3)

    def score(self, metrics: Dict, fold_metrics: List[Dict] = None) -> float:
        """
        Calculate score for a candidate.
        Returns -1.0 if rejected.
        """
        if not metrics:
            return -1.0

        # 1. Hard Gates
        if metrics["total_trades"] < self.min_trades:
            return -1.0
        if metrics["max_dd"] < -abs(self.max_dd/100.0): # metrics['max_dd'] is negative e.g. -0.40
            return -1.0
        if metrics["profit_factor"] < self.min_pf:
            return -1.0

        # Folds Check
        if fold_metrics:
            positive_folds = sum(1 for m in fold_metrics if m["total_return"] > 0)
            if positive_folds < self.min_folds:
                return -1.0

        # 2. Score Calculation
        # Normalize inputs roughly to [0, 1] range or cap them

        # Sharpe: Target 2.0+
        sharpe = max(0, min(metrics["sharpe"], 4.0)) / 4.0

        # Calmar: Target 3.0+
        calmar = max(0, min(metrics["calmar"], 6.0)) / 6.0

        # CAGR: Target 50%+
        cagr = max(0, min(metrics["cagr"], 1.0)) / 1.0

        # Stability: 1 - (std_dev of fold returns) ?
        # Or fraction of positive folds
        stability = 0.0
        if fold_metrics:
            returns = [m["cagr"] for m in fold_metrics]
            if len(returns) > 0:
                # 1 / (1 + CV) coefficient of variation?
                # Simple: Ratio of positive folds
                stability = sum(1 for r in returns if r > 0) / len(returns)

        # Turnover: Bonus for lower turnover (less costs)
        # Trades per day?
        # Let's say optimal is 1-5 trades per day. Too many > 20 is bad.
        # Just use raw trades count inverse?
        # Actually plan says "Low turnover bonus (or -turnover penalty)".
        # Let's use profit factor as proxy for efficiency?
        # Or just 1.0 (placeholder)
        turnover_score = 0.5

        # Sanity
        sanity_score = 1.0 # Placeholder

        total_score = (
            self.w_sharpe * sharpe +
            self.w_calmar * calmar +
            self.w_cagr * cagr +
            self.w_stability * stability +
            self.w_turnover * turnover_score +
            self.w_sanity * sanity_score
        )

        return total_score

    def blend_scores(self, score_15m: float, score_5m: float) -> float:
        """
        Blend scores with 15m preference.
        """
        if score_15m < 0 and score_5m < 0:
            return -1.0
        if score_15m < 0:
            return score_5m
        if score_5m < 0:
            return score_15m

        return 0.6 * score_15m + 0.4 * score_5m
