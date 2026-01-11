from typing import List, Dict, Any
import pandas as pd

class Ranker:
    def rank(self, candidates: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Rank candidates based on composite score.
        Score = 0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*Turnover
        """
        rows = []
        for c in candidates:
            m = c["result"]["metrics"]
            stab = c["result"]["stability"]

            # Normalize inputs roughly to 0-1 range or just raw?
            # User provided weights for raw metrics? Usually we standardize.
            # But let's apply weights to raw first, assuming they are somewhat comparable.
            # Sharpe ~ 1-3
            # Calmar ~ 1-5
            # CAGR ~ 0.2-0.5
            # Stability ~ ? (Inverse std dev of sharpe). If std is 0.5, stab is 2.
            # Turnover ~ ? (Need proxy).

            # Turnover proxy: Average trades per day? Or total trades?
            # "exposure %, turnover proxy"
            # Let's use trades count / days as turnover proxy.
            trades_per_year = m["trades"] / 10.0 # Approx 10y
            turnover_score = trades_per_year / 252.0 # ~ daily turnover freq

            score = (0.3 * m["sharpe"]) + \
                    (0.25 * m["calmar"]) + \
                    (0.2 * m["cagr"] * 100) + \
                    (0.15 * stab) - \
                    (0.1 * turnover_score * 100) # Penalty

            row = {
                "id": c["strategy"].id,
                "score": score,
                "sharpe": m["sharpe"],
                "calmar": m["calmar"],
                "cagr": m["cagr"],
                "max_dd": m["max_drawdown"],
                "trades": m["trades"],
                "stability": stab,
                "rule_summary": c["strategy"].rule_summary,
                "strategy_obj": c["strategy"]
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df.sort_values("score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)

        return df
