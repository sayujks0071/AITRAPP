"""
Promotion Logic
Decides if a candidate should replace the current champion.
"""
class Promoter:
    @staticmethod
    def should_promote(challenger_metrics: dict, champion_metrics: dict | None) -> bool:
        challenger_score = challenger_metrics.get('score', 0.0)

        if not champion_metrics:
            return True

        champion_score = champion_metrics.get('score', 0.0)

        # Rule: Beat score by >= 10%
        if champion_score == 0 or challenger_score >= champion_score * 1.1:
            return True

        champ_dd = champion_metrics.get('max_drawdown', 1.0)
        challenger_dd = challenger_metrics.get('max_drawdown', 1.0)
        champ_sharpe = champion_metrics.get('sharpe', 0.0)
        challenger_sharpe = challenger_metrics.get('sharpe', 0.0)

        # Rule: Reduce MaxDD by >= 5% absolute, without degrading Sharpe
        if (champ_dd - challenger_dd >= 0.05) and \
           (challenger_sharpe >= champ_sharpe * 0.9):
            return True

        return False
