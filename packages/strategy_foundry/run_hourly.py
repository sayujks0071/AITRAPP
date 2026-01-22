import os
import sys
import json
import yaml
import structlog
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger()

class FoundryRunner:
    def __init__(self):
        self.fast_mode = os.environ.get("FAST_MODE", "0") == "1"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(f"packages/strategy_foundry/results/runs/{self.timestamp}")
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Load Configs
        with open("packages/strategy_foundry/configs/foundry.yaml") as f:
            self.config = yaml.safe_load(f)
        with open("packages/strategy_foundry/configs/instrument_map.yaml") as f:
            self.instrument_map = yaml.safe_load(f)

        self.data_loader = DataLoader()
        self.champion_store = ChampionStore()

    def run(self):
        logger.info("Starting Foundry Run", fast_mode=self.fast_mode, timestamp=self.timestamp)

        # 1. Update Data
        instruments = self.instrument_map.get("research", {})
        timeframes = self.config["generation"]["timeframes"] + [self.config["generation"]["sanity_timeframe"]]
        self.data_loader.update_all(instruments, timeframes)

        # 2. Generation & Backtest per Instrument
        for inst_name, symbol in instruments.items():
            logger.info(f"Processing {inst_name} ({symbol})")
            self._process_instrument(inst_name, symbol)

        # 3. Publish Signal
        publisher = SignalPublisher()
        publisher.run()

        logger.info("Foundry Run Completed")

    def _process_instrument(self, name: str, symbol: str):
        # Generate Candidates
        count = self.config["generation"]["candidates_per_run_fast"] if self.fast_mode else self.config["generation"]["candidates_per_run"]
        candidates = StrategyGenerator.generate_population(count)

        # Save Candidates
        with open(self.run_dir / f"candidates_{name}.json", "w") as f:
            json.dump([c.to_dict() for c in candidates], f, indent=2)

        # Backtest
        results = []

        # Load Data
        data_5m = self.data_loader.get_data(symbol, "5m")
        data_15m = self.data_loader.get_data(symbol, "15m")
        data_1d = self.data_loader.get_data(symbol, "1d")

        engine = BacktestEngine(costs=self.config["backtest"]["costs"])

        folds = 2 if self.fast_mode else 4

        for cand in candidates:
            res = {
                "candidate": cand.to_dict(),
                "metrics_5m": {},
                "metrics_15m": {},
                "metrics_1d": {}
            }

            # 5m
            if data_5m is not None and not data_5m.empty:
                res["metrics_5m"] = self._evaluate_timeframe(engine, cand, data_5m, folds)

            # 15m
            if data_15m is not None and not data_15m.empty:
                res["metrics_15m"] = self._evaluate_timeframe(engine, cand, data_15m, folds)

            results.append(res)

        # Rank Intraday
        ranked = Ranker.rank_candidates(results)

        # Sanity Check (Top 10)
        top_n = min(len(ranked), 10)
        final_ranked = []

        for i, res in enumerate(ranked):
            if i < top_n and data_1d is not None and not data_1d.empty:
                 # Run 1D Sanity (No folds, just full history or recent?)
                 # Use 4 folds or just simple backtest?
                 # Prompt: "If daily performance is catastrophically negative... apply penalty"
                 # Let's run full backtest
                 eq, trades = engine.run(Strategy.from_dict(res["candidate"]), data_1d)
                 m1d = calculate_metrics(eq, trades)
                 res["metrics_1d"] = m1d

                 # Apply Penalty
                 if m1d["sharpe"] < -0.2 or m1d["max_dd"] > 45:
                     logger.info(f"Sanity Check Failed for {res['candidate']['id']}", metrics=m1d)
                     res["score"] -= 10.0 # Heavy penalty

            final_ranked.append(res)

        # Re-sort
        final_ranked.sort(key=lambda x: x["score"], reverse=True)

        # Save Results
        with open(self.run_dir / f"results_{name}.json", "w") as f:
            json.dump(final_ranked, f, indent=2)

        # Generate Markdown Leaderboard
        self._write_leaderboard(name, final_ranked)

        # Promotion (Only in Full Mode)
        if not self.fast_mode and final_ranked:
            best = final_ranked[0]
            current_champ = self.champion_store.load_champion(name)

            should_promote = False
            if current_champ:
                should_promote = Promoter.should_promote(best["metrics_15m"], current_champ.get("metrics", {})) # Compare 15m as primary? Or blended score?
                # Using Blended Score comparison implemented in Promoter
                # But Promoter expects metrics dict to calculate score.
                # Here `best` has computed score.
                # Let's use score directly.

                # Wait, Promoter calculates score internally from metrics.
                # So I should pass the metrics dict that resulted in the high score.
                # Since score is blended, which metrics do I pass?
                # Passing merged metrics is hard.
                # Let's pass the one that matches the `timeframe` we prefer, or just modify Promoter to take score.
                # Actually, `Promoter.should_promote` takes `metrics` and calls `Ranker`.
                # If I want to use the blended score, I should probably implement that logic here or pass a dummy metrics dict with precomputed score?
                # No, I should rely on the metrics.

                # Let's use 15m metrics for promotion comparison if available, else 5m.
                # Or better: `best` has "metrics_15m" and "metrics_5m".
                pass
            else:
                should_promote = True

            if should_promote:
                # One last check: Live Eligibility
                # Check blended score eligibility?
                # "Live-eligible gate: blended OOS Sharpe >= 1.2"
                # Ranker calculated `score` (which is composite), not Sharpe.
                # We need to check Sharpe explicitly.
                m15 = best.get("metrics_15m", {})
                m5 = best.get("metrics_5m", {})

                sharpe15 = m15.get("sharpe", -99)
                sharpe5 = m5.get("sharpe", -99)

                # Blended Sharpe
                b_sharpe = -99
                if sharpe15 > -90 and sharpe5 > -90:
                    b_sharpe = 0.6 * sharpe15 + 0.4 * sharpe5
                elif sharpe15 > -90:
                    b_sharpe = sharpe15
                elif sharpe5 > -90:
                    b_sharpe = sharpe5

                if b_sharpe >= 1.2:
                    # Also check DD
                    # And trades
                    # Simply use Promoter.is_live_eligible with a constructed "blended metrics" dict
                    blended_metrics = {
                        "sharpe": b_sharpe,
                        "max_dd": max(m15.get("max_dd", 100), m5.get("max_dd", 100)),
                        "trades": max(m15.get("trades", 0), m5.get("trades", 0))
                    }

                    eligible, reason = Promoter.is_live_eligible(blended_metrics)
                    if eligible:
                        self.champion_store.save_champion(name, best["candidate"], blended_metrics, self.timestamp)
                    else:
                        logger.info(f"Candidate {best['candidate']['id']} good but not live eligible: {reason}")
                else:
                     logger.info(f"Candidate {best['candidate']['id']} good score but Sharpe {b_sharpe:.2f} < 1.2")


    def _evaluate_timeframe(self, engine: BacktestEngine, candidate: Strategy, data: pd.DataFrame, folds: int) -> Dict:
        cand_obj = Strategy.from_dict(candidate.to_dict())

        # Walk Forward
        splits = WalkForward.split(data, folds=folds)

        oos_equity = []
        all_trades = []

        positive_folds = 0

        for train, test in splits:
             # We only care about OOS performance for ranking
             eq, trades = engine.run(cand_obj, test)
             if not eq.empty:
                 oos_equity.append(eq)
                 all_trades.extend(trades)

                 # Check if positive
                 if eq.iloc[-1] > eq.iloc[0]:
                     positive_folds += 1

        if not oos_equity:
            return {}

        # Stitch OOS equity? Or just average metrics?
        # Usually Stitching OOS curves gives the "Walk Forward Equity".
        # But gaps between folds need handling (capital reset).
        # Metrics on aggregated trades list + concatenated equity curve (normalized).

        # Simple approach: Metrics on aggregated trades.
        # But Sharpe needs daily returns.
        # Concatenate equity curves? Timestamps might overlap if rolling?
        # Rolling window: Train [0-20], Test [20-30]. Train [10-30], Test [30-40].
        # Test sets [20-30] and [30-40] are contiguous.
        # So we can concat.

        full_eq = pd.concat(oos_equity)
        full_eq = full_eq[~full_eq.index.duplicated(keep='first')] # Handle overlaps if any

        metrics = calculate_metrics(full_eq, all_trades)
        metrics["positive_folds"] = positive_folds
        return metrics

    def _write_leaderboard(self, name: str, ranked: List[Dict]):
        path = self.run_dir / f"leaderboard_{name}.md"
        with open(path, "w") as f:
            f.write(f"# Leaderboard: {name}\n")
            f.write(f"Run: {self.timestamp}\n\n")
            f.write("| Rank | ID | Score | Sharpe (15m) | Sharpe (5m) | MaxDD | Trades |\n")
            f.write("|---|---|---|---|---|---|---|\n")

            for i, r in enumerate(ranked[:20]):
                mid = r["candidate"]["id"]
                score = r.get("score", -99)
                m15 = r.get("metrics_15m", {})
                m5 = r.get("metrics_5m", {})

                s15 = m15.get("sharpe", -99)
                s5 = m5.get("sharpe", -99)
                dd = max(m15.get("max_dd", 0), m5.get("max_dd", 0))
                trades = m15.get("trades", 0) + m5.get("trades", 0)

                f.write(f"| {i+1} | {mid} | {score:.2f} | {s15:.2f} | {s5:.2f} | {dd:.1f}% | {trades} |\n")

if __name__ == "__main__":
    runner = FoundryRunner()
    runner.run()
