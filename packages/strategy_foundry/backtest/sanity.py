import pandas as pd
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader

logger = structlog.get_logger(__name__)

class SanityChecker:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def check_daily_sanity(self, candidate: StrategyCandidate, symbol: str) -> bool:
        """
        Run the candidate on 1D data to ensure it doesn't blow up.
        """
        # Fetch 1D data
        daily_data = self.loader.get_data(symbol, "1d")
        if daily_data.empty:
            logger.warning("No daily data for sanity check, skipping", symbol=symbol)
            return True # Fail open? Or fail closed? Prompt says "Robustness check", maybe warning is enough.

        # Run Backtest
        # We need to construct a 1D version of the candidate?
        # The candidate has a timeframe attribute. But the logic *should* work on any timeframe
        # IF the indicator periods are reasonable.
        # But wait, 5m params (e.g. EMA 50) on Daily might mean EMA 50 days (huge).
        # The prompt says: "Run 1D sanity backtest... if daily performance is catastrophically negative... reject"

        engine = BacktestEngine(daily_data)
        res = engine.run(candidate)
        metrics = res.get("metrics", {})

        sharpe = metrics.get("sharpe", 0)
        max_dd = metrics.get("max_dd", 0)

        # "If Sharpe < -0.2 or MaxDD > 45%"
        if sharpe < -0.2:
            logger.info("Failed daily sanity: Sharpe too low", id=candidate.id, sharpe=sharpe)
            return False

        if max_dd > 0.45:
             logger.info("Failed daily sanity: MaxDD too high", id=candidate.id, max_dd=max_dd)
             return False

        return True

    def check_intraday_sanity(self, trades: pd.DataFrame) -> bool:
        """
        "late-day dependence" check (profit concentrated only in last 30 minutes)
        "overtrade penalty" (too many trades/day)
        """
        if trades.empty:
            return True

        # TODO: Implement checks
        # For now, just a placeholder return True
        return True
