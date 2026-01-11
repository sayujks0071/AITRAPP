from typing import Dict, Any

class Promoter:
    def should_promote(self, challenger_score: float, challenger_metrics: Dict[str, Any],
                       incumbent_score: float, incumbent_metrics: Dict[str, Any]) -> bool:
        """
        Promotion rule:
        - New score >= Current score * 1.10 (10% improvement)
        - OR Lower MaxDD materially (e.g. 20% relative reduction) AND score >= current score
        """
        if incumbent_score is None:
            return True

        if challenger_score >= incumbent_score * 1.10:
            return True

        # Check DD improvement
        curr_dd = incumbent_metrics.get("max_drawdown", 1.0)
        new_dd = challenger_metrics.get("max_drawdown", 1.0)

        if new_dd < curr_dd * 0.8 and challenger_score >= incumbent_score:
            return True

        return False
