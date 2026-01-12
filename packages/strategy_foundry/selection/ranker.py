from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = structlog.get_logger(__name__)

class Ranker:
    def __init__(self, config: Dict):
        self.config = config

    def rank(self, candidates: List[Dict], timeframe: str) -> pd.DataFrame:
        """
        Rank candidates based on OOS metrics.
        Input: list of dicts with 'candidate', 'metrics', 'folds'.
        """
        if not candidates:
            return pd.DataFrame()

        rows = []
        for item in candidates:
            m = item["metrics"]["aggregate"]
            c = item["candidate"]

            # Apply Gates
            if not self._check_gates(m, timeframe):
                continue

            score = self._compute_score(m, item["metrics"]["folds"])

            rows.append({
                "id": c.id,
                "score": score,
                "sharpe": m["sharpe"],
                "calmar": m["calmar"],
                "cagr": m["cagr"],
                "max_dd": m["max_dd_pct"],
                "trades": m["total_trades"],
                "win_rate": m["win_rate"],
                "pf": m["profit_factor"],
                "candidate_obj": c # Keep for storage
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("score", ascending=False).reset_index(drop=True)

        return df

    def _check_gates(self, m: Dict, timeframe: str) -> bool:
        ranking_cfg = self.config.get("ranking", {})

        # Min Trades
        min_trades = ranking_cfg.get(f"min_trades_{timeframe}", 20)
        if m["total_trades"] < min_trades:
            return False

        # Max DD
        if m["max_dd_pct"] > ranking_cfg.get("max_dd_pct", 30.0):
            return False

        # Profit Factor
        if m["profit_factor"] < ranking_cfg.get("min_profit_factor", 1.1):
            return False

        return True

    def _compute_score(self, m: Dict, folds: List[Dict]) -> float:
        # Score weights:
        # + 25% OOS Sharpe
        # + 25% OOS Calmar
        # + 20% Net return / CAGR (Normalized?)
        # + 15% Stability (low variance across folds)
        # + 10% Low turnover bonus ?? Or just higher returns handles it?

        # Normalize somewhat to make them comparable
        # Sharpe > 2 is great. Calmar > 2 is great.

        sharpe_score = min(max(m["sharpe"], 0), 3.0) / 3.0
        calmar_score = min(max(m["calmar"], 0), 3.0) / 3.0

        # Stability: Fraction of profitable folds
        positive_folds = sum(1 for f in folds if f["net_return_pct"] > 0)
        stability_score = positive_folds / len(folds) if folds else 0

        # CAGR score (cap at 100%)
        cagr_score = min(max(m["cagr"], -0.5), 1.0)

        score = (0.25 * sharpe_score) + (0.25 * calmar_score) + (0.20 * cagr_score) + (0.30 * stability_score)

        return score
