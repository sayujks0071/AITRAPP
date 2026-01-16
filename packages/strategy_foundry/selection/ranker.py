import pandas as pd
from typing import List, Dict, Any

class Ranker:
    @staticmethod
    def rank(results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Ranks strategies based on weighted score.
        results: list of {strategy: Config, metrics: {overall:..., stability:...}}
        """
        if not results:
            return pd.DataFrame()

        rows = []
        for res in results:
            strat = res['strategy']
            m = res['metrics']
            ov = m['overall']
            stab = m['stability']

            # Score Components
            # 1. Sharpe (25%)
            # Cap Sharpe at 3.0 to avoid outliers domination
            sharpe_score = min(max(ov['sharpe'], 0), 3.0) / 3.0

            # 2. Calmar (25%)
            # Cap Calmar at 10
            calmar_score = min(max(ov['calmar'], 0), 10.0) / 10.0

            # 3. Net Return (20%)
            # Log return? Or simple cap?
            # Assume 100% return is great.
            ret_score = min(max(ov['net_return'], 0), 1.0)

            # 4. Stability (15%)
            # Low variance is good.
            # 1 - (std / 2.0) capped
            stab_score = max(0, 1 - (stab['sharpe_std'] / 2.0))

            # 5. Low Turnover / Efficiency (10%)
            # We want efficiency but not excessive trading.
            # Maybe Profit Factor is better proxy for efficiency?
            # Let's use Profit Factor / 3.0
            eff_score = min(max(ov['profit_factor'], 0), 3.0) / 3.0

            # Total Score
            score = (0.25 * sharpe_score +
                     0.25 * calmar_score +
                     0.20 * ret_score +
                     0.15 * stab_score +
                     0.15 * eff_score) * 100.0

            rows.append({
                "strategy_id": strat.strategy_id,
                "score": score,
                "net_return": ov['net_return'],
                "sharpe": ov['sharpe'],
                "max_dd": ov['max_drawdown'],
                "calmar": ov['calmar'],
                "trades": ov['total_trades'],
                "profit_factor": ov['profit_factor'],
                "sharpe_std": stab['sharpe_std'],
                "positive_folds": stab['positive_folds']
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df.sort_values('score', ascending=False, inplace=True)

        return df
