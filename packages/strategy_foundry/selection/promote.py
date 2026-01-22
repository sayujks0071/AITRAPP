from typing import Dict, Tuple
import structlog
from packages.strategy_foundry.selection.ranker import Ranker

logger = structlog.get_logger(__name__)

class Promoter:
    """
    Decides if a challenger should replace the incumbent.
    """

    @staticmethod
    def should_promote(challenger_metrics: Dict, incumbent_metrics: Dict) -> bool:
        """
        Promotion Logic:
        1. Score improvement > 10%
        OR
        2. Drawdown reduction > 5% (absolute) with similar score (>= 95% of incumbent)
        """
        if not incumbent_metrics:
            return True # No incumbent, promote

        s_challenger = Ranker.calculate_score(challenger_metrics)
        s_incumbent = Ranker.calculate_score(incumbent_metrics)

        if s_incumbent <= 0:
             return s_challenger > s_incumbent

        # 1. Score Improvement
        score_imp = (s_challenger - s_incumbent) / abs(s_incumbent)
        if score_imp >= 0.10:
            logger.info("Promoting on score", improvement=score_imp)
            return True

        # 2. Safety Improvement
        dd_challenger = challenger_metrics.get("max_dd", 100)
        dd_incumbent = incumbent_metrics.get("max_dd", 100)

        if (dd_incumbent - dd_challenger) >= 5.0: # 5% absolute reduction
             if s_challenger >= (s_incumbent * 0.95):
                 logger.info("Promoting on safety", dd_reduction=dd_incumbent-dd_challenger)
                 return True

        return False

    @staticmethod
    def is_live_eligible(metrics: Dict) -> Tuple[bool, str]:
        """
        Strict gates for live signal publishing.
        """
        sharpe = metrics.get("sharpe", 0)
        max_dd = metrics.get("max_dd", 100)
        trades = metrics.get("trades", 0)

        if sharpe < 1.2:
            return False, f"Sharpe {sharpe:.2f} < 1.2"
        if max_dd > 20.0:
            return False, f"MaxDD {max_dd:.1f}% > 20%"
        if trades < 20: # Minimum sample size
             return False, f"Trades {trades} < 20"

        return True, "OK"
