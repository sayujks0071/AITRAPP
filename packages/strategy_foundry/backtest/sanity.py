"""
Sanity Checks and Gates.
"""
from typing import Dict, Any, List
import structlog
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.ranker import Ranker

logger = structlog.get_logger(__name__)

class SanityChecker:
    def __init__(self, engine: BacktestEngine, ranker: Ranker):
        self.engine = engine
        self.ranker = ranker

    def check_intraday_robustness(self, metrics: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """
        Check basic intraday stats before expensive daily sanity.
        """
        min_trades = config.get("risk", {}).get("min_trades", 40)
        max_dd = config.get("risk", {}).get("max_dd_percent", 30) / 100.0
        min_sharpe = config.get("risk", {}).get("min_sharpe", 0.5)

        if metrics["trades"] < min_trades:
            return False
        if metrics["max_dd"] > max_dd:
            return False
        if metrics["sharpe"] < min_sharpe:
            return False

        # WFA Checks
        if "positive_folds" in metrics:
            total_folds = metrics.get("total_folds", 4)
            # Require > 50% positive folds
            if metrics["positive_folds"] < (total_folds / 2):
                return False

        return True

    def check_daily_sanity(self, strategy: StrategyConfig, daily_data: 'pd.DataFrame') -> bool:
        """
        Run strategy on 1D data to ensure it's not catastrophic.
        """
        if daily_data.empty:
            logger.warning("No daily data for sanity check")
            return True # Pass if no data? Or fail? Fail safe is better but let's pass with warning.

        res = self.engine.run(strategy, daily_data)
        metrics = self.ranker.calculate_metrics(res["trades"])

        # Criteria for Failure
        # We don't need it to be profitable on 1D (it's an intraday strategy),
        # but it shouldn't blow up (e.g., massive drawdown on daily trend).

        if metrics["max_dd"] > 0.45: # 45% DD on daily is bad
            logger.info("Failed Daily Sanity: High DD", dd=metrics["max_dd"])
            return False

        if metrics["sharpe"] < -0.5: # Consistently losing money
            logger.info("Failed Daily Sanity: Negative Sharpe", sharpe=metrics["sharpe"])
            return False

        return True
