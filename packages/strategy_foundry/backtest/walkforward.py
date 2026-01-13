"""Walk-Forward Analysis"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import structlog
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = structlog.get_logger(__name__)

class WalkForward:
    def __init__(self, data: pd.DataFrame, folds: int = 4):
        self.data = data
        self.folds = folds

    def run(self, candidate, engine_cls=BacktestEngine) -> Dict[str, Any]:
        # Split data into folds
        n = len(self.data)
        fold_size = n // self.folds

        # Run on full dataset
        engine = engine_cls(self.data)
        full_res = engine.run(candidate)

        idx = self.data.index
        fold_len = len(idx) // self.folds

        fold_scores = []

        for i in range(self.folds):
            start = i * fold_len
            end = (i + 1) * fold_len
            sub_df = self.data.iloc[start:end]

            # Skip if too small
            if len(sub_df) < 100: continue

            eng = engine_cls(sub_df)
            res = eng.run(candidate)

            # Check pass/fail
            score = 0.0
            if res["total_return"] > 0: score += 1
            if res["sharpe"] > 0.5: score += 1

            fold_scores.append({
                "fold": i,
                "return": res["total_return"],
                "sharpe": res["sharpe"],
                "trades": res["trades"]
            })

        # Aggregate
        positive_folds = len([f for f in fold_scores if f["return"] > 0])
        avg_sharpe = np.mean([f["sharpe"] for f in fold_scores]) if fold_scores else 0

        return {
            "full_result": full_res,
            "folds": fold_scores,
            "consistency": positive_folds / self.folds,
            "avg_sharpe": avg_sharpe
        }
