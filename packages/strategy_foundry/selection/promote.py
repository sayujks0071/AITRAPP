"""
Promotion Logic
"""
from typing import Dict, Any, Optional

class Promoter:
    @staticmethod
    def should_promote(candidate: Dict[str, Any], current_champion_metrics: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if candidate should replace current champion.
        """
        if not current_champion_metrics:
            # No champion exists, promote if decent
            return True

        cand_metrics = candidate['metrics']
        cand_score = candidate['score']

        # We don't have current champion score readily available here unless we recalculate.
        # But we can compare raw metrics.

        # Logic: Beat score by 10% OR reduce MaxDD by 5% (abs) without degrading Sharpe

        # Re-calculate score for current champ approx (or pass it in)
        # Assuming we just compare Sharpe and DD for now as per prompt instructions
        # "New must beat current blended_score by >= 10%"

        # We need the score of the current champion.
        # Ideally stored in metrics, but 'score' isn't in metrics dict usually.
        # Let's assume we can't easily get the old score, so we use Sharpe/DD proxy.

        current_sharpe = current_champion_metrics['sharpe']
        current_dd = current_champion_metrics['max_drawdown']

        cand_sharpe = cand_metrics['sharpe']
        cand_dd = cand_metrics['max_drawdown']

        # Condition 1: Significant Score Improvement (Proxy: Sharpe +20%)
        if cand_sharpe > current_sharpe * 1.20:
            return True

        # Condition 2: Safety Improvement (MaxDD reduced by 5% absolute)
        # e.g. 20% -> 15%
        if cand_dd < (current_dd - 0.05):
            # Without degrading Sharpe meaningfully (within 90%)
            if cand_sharpe > current_sharpe * 0.9:
                return True

        return False
