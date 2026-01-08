"""
Promotion Logic.
"""
import structlog

logger = structlog.get_logger(__name__)

class Promoter:
    def should_promote(self, challenger: dict, incumbent: dict) -> bool:
        """
        Determine if challenger should replace incumbent.

        Rules:
        - New must beat current blended_score by >= 10%
        - OR reduce MaxDD by >= 5% absolute while not degrading Sharpe meaningfully (> -0.1 change).
        """
        if incumbent is None:
            return True

        c_score = challenger.get("score", 0)
        i_score = incumbent.get("score", 0)

        c_dd = challenger["metrics"]["max_dd"]
        i_dd = incumbent["metrics"]["max_dd"]

        c_sharpe = challenger["metrics"]["sharpe"]
        i_sharpe = incumbent["metrics"]["sharpe"]

        # 1. Score Improvement
        if c_score >= i_score * 1.10:
            logger.info("Promoting: Score improvement", challenger=c_score, incumbent=i_score)
            return True

        # 2. Risk Reduction
        if (i_dd - c_dd) >= 0.05:
            # Check Sharpe degradation
            if (c_sharpe - i_sharpe) > -0.1:
                logger.info("Promoting: Risk reduction", challenger_dd=c_dd, incumbent_dd=i_dd)
                return True

        return False
