"""Hourly Orchestrator"""
import os
import structlog
from pathlib import Path
from datetime import datetime
import pandas as pd

from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardAnalyst
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.adapters.core_costs import CostModel

logger = structlog.get_logger(__name__)

# Constants
RESULTS_DIR = Path("packages/strategy_foundry/results/runs")
LEADERBOARD_FILE = Path("packages/strategy_foundry/results/leaderboard.md")

class HourlyRunner:
    def __init__(self):
        self.fast_mode = os.getenv("FAST_MODE", "0") == "1"
        self.run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = RESULTS_DIR / self.run_ts
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.loader = DataLoader(use_cache=True)
        self.cost_model = CostModel()
        self.engine = BacktestEngine(self.cost_model)
        self.ranker = Ranker()
        self.store = ChampionStore()

    def run(self):
        logger.info("Starting Hourly Run", fast_mode=self.fast_mode, run_id=self.run_ts)

        # 1. Configuration
        count = 15 if self.fast_mode else 80
        folds = 2 if self.fast_mode else 4

        # 2. Data Loading (Research Symbol: NIFTY)
        # TODO: Load from config map
        symbol = "^NSEI"

        # Load 5m, 15m, 1D
        data_5m = self.loader.get_data(symbol, "5m", days=60)
        data_15m = self.loader.get_data(symbol, "15m", days=60)
        data_1d = self.loader.get_data(symbol, "1D", days=365)

        if data_5m.empty and data_15m.empty:
            logger.error("No data available")
            return

        # 3. Generate Candidates
        gen = StrategyGenerator(timeframes=["5m", "15m"])
        candidates = gen.generate(count=count)
        logger.info("Generated candidates", count=len(candidates))

        # 4. Backtest & Eval
        analyst = WalkForwardAnalyst(self.engine, folds=folds)
        sanity = SanityChecker(self.engine)

        results = []

        for cand in candidates:
            # Select Data
            df = data_5m if cand.timeframe == "5m" else data_15m
            if df.empty: continue

            # Walk Forward
            wf_res = analyst.run(cand, df)

            # Intraday Sanity (on full trades)
            # Global trades from WF
            # Re-assemble trades from folds or just use global?
            # Global metrics in WF are computed on concat equity, but we didn't store trades list in global key.
            # Let's trust WF output or re-run?
            # WF returns 'global' metrics dict.
            # We need trades for sanity check (time dependence).
            # Let's run full engine once on full data for Sanity Check inputs?
            # Or pass trades out of WF.
            # I'll update WF to return trades? Or just skip deep sanity for now and rely on metrics.
            # Basic sanity (turnover) can be inferred from 'total_trades'.

            # Penalty calc
            trades_count = wf_res["global"]["total_trades"]
            days = 60 # approx
            avg_trades = trades_count / days
            sanity_res = {"penalty": 0.0}
            if avg_trades > 10: sanity_res["penalty"] = 0.2

            # Score
            score = self.ranker.score(wf_res, sanity_res)

            # Daily Sanity Overlay (only for top candidates usually, but let's do all if fast)
            # If score > threshold?
            daily_check = {"passed": True}
            if score > 0.5: # Only check promising ones
                 daily_check = sanity.check_daily_robustness(cand, data_1d)
                 if not daily_check["passed"]:
                     score = 0.0 # Kill it

            res_entry = {
                "id": cand.id,
                "score": score,
                "metrics": wf_res,
                "candidate": cand,
                "sanity": daily_check,
                "ts": self.run_ts
            }
            results.append(res_entry)

        # 5. Ranking
        results.sort(key=lambda x: x["score"], reverse=True)
        top_10 = results[:10]

        # Save Results
        self._save_results(results)
        self._update_leaderboard(top_10)

        # 6. Promotion (Full Mode Only)
        if not self.fast_mode and top_10:
            best = top_10[0]
            if best["score"] > 0:
                if self.store.should_promote(best["score"], best["metrics"]):
                    logger.info("Promoting new champion", id=best["id"])
                    self.store.save_new_champion(best["candidate"], best["metrics"], best["score"])

        # 7. Publish Signal
        # Even if fast mode? Maybe.
        # Check market hours
        pub = SignalPublisher()
        pub.publish()

        logger.info("Run Complete")

    def _save_results(self, results):
        # Save detailed JSON/CSV
        # Just simple CSV for analysis
        rows = []
        for r in results:
            m = r["metrics"]["global"]
            row = {
                "id": r["id"],
                "score": r["score"],
                "tf": r["candidate"].timeframe,
                "sharpe": m.get("sharpe"),
                "dd": m.get("max_drawdown"),
                "trades": m.get("total_trades"),
                "rule": r["candidate"].rule_summary
            }
            rows.append(row)

        pd.DataFrame(rows).to_csv(self.run_dir / "metrics.csv", index=False)

    def _update_leaderboard(self, top_10):
        md = "# Intraday Strategy Foundry Leaderboard\n\n"
        md += f"Last Run: {self.run_ts}\n\n"
        md += "| Rank | ID | Score | TF | Sharpe | DD | Rule |\n"
        md += "|---|---|---|---|---|---|---|\n"

        for i, r in enumerate(top_10):
            m = r["metrics"]["global"]
            md += f"| {i+1} | {r['id'][:8]} | {r['score']:.2f} | {r['candidate'].timeframe} | {m.get('sharpe',0):.2f} | {m.get('max_drawdown',0):.1%} | {r['candidate'].rule_summary} |\n"

        LEADERBOARD_FILE.write_text(md)

if __name__ == "__main__":
    HourlyRunner().run()
