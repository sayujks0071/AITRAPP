"""
Sanity checks and anti-overfitting gates.
"""
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)

class SanityCheck:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def check_intraday(self, metrics: Dict[str, Any], wf_results: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if intraday candidate passes filters.
        """
        reasons = []
        passed = True

        # 1. Trade Count
        min_trades = 40 # Default
        if "candidates_per_run_fast" in self.config and metrics.get("trades", 0) < 20: # Heuristic for fast mode
             pass
        elif metrics["trades"] < min_trades:
            reasons.append(f"Too few trades: {metrics['trades']}")
            passed = False

        # 2. Max DD
        if metrics["max_dd"] > 0.30:
            reasons.append(f"High Drawdown: {metrics['max_dd']:.2%}")
            passed = False

        # 3. Profit Factor
        if metrics["profit_factor"] < 1.1:
            reasons.append(f"Low PF: {metrics['profit_factor']:.2f}")
            passed = False

        # 4. Consistency
        needed = 3 if wf_results["n_folds"] >= 4 else 1
        if wf_results["consistency"] < needed:
            reasons.append(f"Inconsistent: {wf_results['consistency']}/{wf_results['n_folds']}")
            passed = False

        return passed, reasons

    def check_daily_sanity(self, metrics_1d: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check 1D sanity results.
        Not strict profit requirement, but no catastrophe.
        """
        reasons = []
        passed = True

        if metrics_1d["sharpe"] < -0.5:
            reasons.append(f"Daily Catastrophe: Sharpe {metrics_1d['sharpe']:.2f}")
            passed = False

        if metrics_1d["max_dd"] > 0.45:
            reasons.append(f"Daily Catastrophe: DD {metrics_1d['max_dd']:.2%}")
            passed = False

        return passed, reasons
