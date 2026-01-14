import pandas as pd
import numpy as np

class Ranker:
    @staticmethod
    def score(metrics_list: list[dict]) -> float:
        """
        Computes composite score from fold metrics.
        We treat the LAST fold as OOS?
        Or all folds are OOS because we haven't trained?

        Requirement: "Ranking uses OUT-OF-SAMPLE metrics only."
        If we consider the generation random, and we select based on this score,
        then the data used for this score BECOMES In-Sample.

        But if we use Walk-Forward (Train/Test splits), we usually aggregate the Test results.

        Let's assume `metrics_list` contains metrics for [Fold1, Fold2, Fold3].
        If we just want stability, we average them.

        Let's implement the default weights:
        + 30% Sharpe
        + 25% Calmar
        + 20% CAGR
        + 15% Stability (low dispersion of Sharpe)
        - 10% Turnover penalty

        We will calculate these stats across the folds.
        Average Sharpe, Average Calmar, Average CAGR.
        Stability = 1 / (StdDev(Sharpe) + 1).

        Turnover = Avg Trades / Days? Or Portfolio Turnover.
        We have 'trades' count.

        """
        if not metrics_list:
            return -999.0

        sharpes = [m.get('sharpe', 0) for m in metrics_list]
        calmars = [m.get('calmar', 0) for m in metrics_list]
        cagrs = [m.get('cagr', 0) for m in metrics_list]

        avg_sharpe = np.mean(sharpes)
        avg_calmar = np.mean(calmars)
        avg_cagr = np.mean(cagrs)

        sharpe_std = np.std(sharpes)
        stability = 1.0 / (sharpe_std + 0.1) # Higher is better

        # Turnover proxy: Average trades per fold (normalized by length?)
        # Let's just use raw count penalty if high.
        avg_trades = np.mean([m.get('trades', 0) for m in metrics_list])

        # Penalize if too many trades (overtrading/costs) or too few
        # Penalty logic:
        # "Turnover penalty" usually means `Portfolio Turnover %`.
        # We don't have exact turnover.
        # Let's map avg_trades to a 0-1 score where optimum is e.g. 50-100?
        # For now, simplistic: -0.1 * log(trades)?
        # Let's use 0.0 for now as penalty is vague.
        turnover_penalty = 0.0

        score = (0.30 * avg_sharpe) + \
                (0.25 * avg_calmar) + \
                (0.20 * avg_cagr * 10) + \
                (0.15 * stability) - \
                (0.10 * turnover_penalty)

        # Adjust scale
        return score

    @staticmethod
    def rank(results: list[dict]) -> pd.DataFrame:
        """
        results: list of { 'strategy': config, 'metrics': [fold_metrics], ... }
        Returns sorted DataFrame.
        """
        data = []
        for r in results:
            s_id = r['strategy'].strategy_id
            m_list = r['metrics']
            score = Ranker.score(m_list)

            # Aggregate for display
            avg_sharpe = np.mean([m.get('sharpe', 0) for m in m_list])
            max_dd = np.min([m.get('max_dd', 0) for m in m_list]) # Worst DD

            data.append({
                "strategy_id": s_id,
                "score": score,
                "avg_sharpe": avg_sharpe,
                "max_dd": max_dd,
                "strategy_obj": r['strategy'],
                "metrics_list": m_list
            })

        df = pd.DataFrame(data)
        if not df.empty:
            df.sort_values('score', ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)
        return df
