"""
Promotion Logic
Decides if a candidate should replace the current champion.
"""
class Promoter:
    @staticmethod
    def should_promote(challenger_metrics: dict, champion_metrics: dict) -> bool:
        if not champion_metrics:
            return True

        # Rule: Beat score by >= 10%
        if challenger_metrics['score'] >= champion_metrics['score'] * 1.1:
            return True

        # Rule: Reduce MaxDD by >= 5% absolute, without degrading Sharpe
        if (champion_metrics['max_drawdown'] - challenger_metrics['max_drawdown'] >= 0.05) and \
           (challenger_metrics['sharpe'] >= champion_metrics['sharpe'] * 0.9):
            return True

        return False
