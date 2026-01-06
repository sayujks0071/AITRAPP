"""Sanity checks"""
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class SanityChecker:
    def __init__(self, engine: BacktestEngine):
        self.engine = engine

    def check_daily_robustness(self, candidate: StrategyCandidate, daily_data: pd.DataFrame) -> dict:
        """
        Run 1D backtest as sanity check.
        Rejects if catastrophic failure.
        """
        if daily_data.empty:
            return {"passed": False, "reason": "No Data"}

        eq, trades = self.engine.run_safe(candidate, daily_data)
        metrics = calculate_metrics(trades, eq)

        # Criteria for "Catastrophic Failure" on Daily
        # e.g. MaxDD > 45% or Sharpe < -0.2

        passed = True
        reason = "OK"

        if metrics["max_drawdown"] > 0.45:
            passed = False
            reason = f"Daily MaxDD {metrics['max_drawdown']:.2f} > 0.45"
        elif metrics["sharpe"] < -0.2:
            # Allow slightly negative (it's intraday strategy running on daily, might not fit perfectly)
            # But deep negative implies trend fighting or terrible logic
            passed = False
            reason = f"Daily Sharpe {metrics['sharpe']:.2f} < -0.2"

        return {
            "passed": passed,
            "reason": reason,
            "metrics": metrics
        }

    def check_intraday_sanity(self, trades: list) -> dict:
        """
        Check for:
        - Late day dependence
        - Overtrading
        """
        if not trades:
            return {"penalty": 0.0, "reason": "No Trades"}

        # Late Day Dependence: > 70% of profit comes from last 30 mins?
        # TODO: Implement time-based PnL attribution

        # Overtrading: Trades per day > 20?
        # Extract dates
        dates = set(t.entry_time.date() for t in trades)
        if not dates:
             return {"penalty": 0.0}

        avg_trades_per_day = len(trades) / len(dates)

        penalty = 0.0
        reason = []

        if avg_trades_per_day > 10: # Threshold
             penalty += 0.2
             reason.append(f"High Turnover ({avg_trades_per_day:.1f}/day)")

        return {"penalty": penalty, "reasons": reason}
