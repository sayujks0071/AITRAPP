import os
import time
import structlog
import yaml
import pandas as pd
from typing import List, Dict
from pathlib import Path
from datetime import datetime

from packages.strategy_foundry.factory.generator import StrategyGenerator, StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

class HourlyRunner:
    def __init__(self):
        self.fast_mode = os.getenv("FAST_MODE", "0") == "1"
        self.loader = DataLoader()
        self.generator = StrategyGenerator()

        # Configs
        with open("packages/strategy_foundry/configs/foundry.yaml", "r") as f:
            self.config = yaml.safe_load(f)

        self.engine = BacktestEngine(
            initial_capital=self.config["backtest"]["initial_capital"],
            cost_bps=self.config["backtest"]["cost_bps"],
            slippage_bps=self.config["backtest"]["slippage_bps"]
        )
        self.ranker = Ranker(config=self.config.get("evaluation"))
        self.store = ChampionStore()
        self.publisher = SignalPublisher()

        self.run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path(f"packages/strategy_foundry/results/runs/{self.run_ts}")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        logger.info("Starting Hourly Run", fast_mode=self.fast_mode, ts=self.run_ts)

        # 1. Setup Parameters
        candidates_count = self.config["generation"]["fast_mode_candidates"] if self.fast_mode else self.config["generation"]["candidates_per_run"]
        folds = self.config["evaluation"]["fast_mode_folds"] if self.fast_mode else self.config["evaluation"]["folds"]

        # 2. Generate Candidates
        candidates = self.generator.generate_candidates(candidates_count)
        self._save_candidates(candidates)

        instruments = ["NIFTY", "SENSEX"]
        timeframes = ["5m", "15m"]

        leaderboards = {}

        # 3. Process Instruments
        for instrument in instruments:
            logger.info("Processing Instrument", instrument=instrument)
            symbol = self.get_symbol(instrument)

            instrument_candidates_scores = []

            # Load Data for all timeframes
            data_map = {}
            for tf in timeframes:
                 # Fetch enough data for folds
                 days = 120 # Approx 6 months
                 data_map[tf] = self.loader.get_data(symbol, tf, days=days)

            # 1D Sanity Data
            data_1d = self.loader.get_data(symbol, "1D", days=365)

            # Evaluate Candidates
            for cand in candidates:
                cand_scores = {}
                cand_metrics = {}

                # Backtest on timeframes
                for tf in timeframes:
                    data = data_map[tf]
                    if data.empty:
                        continue

                    # Split into Folds
                    fold_metrics_list = self._run_folds(cand, data, folds)

                    # Aggregate Metrics (Simple Average of folds + Full Run?)
                    # Let's run full backtest for aggregate stats
                    full_res = self.engine.run(cand, data)
                    metrics = full_res.get("metrics", {})

                    if not metrics:
                        continue

                    score = self.ranker.score(metrics, fold_metrics_list)
                    cand_scores[tf] = score
                    cand_metrics[tf] = metrics

                # Blended Score
                s5 = cand_scores.get("5m", -1.0)
                s15 = cand_scores.get("15m", -1.0)
                blended = self.ranker.blend_scores(s15, s5)

                if blended > 0:
                    # Sanity Check 1D
                    sanity_res = self.engine.run(cand, data_1d)
                    sanity_metrics = sanity_res.get("metrics", {})

                    # Simple Sanity Gate
                    if sanity_metrics and (sanity_metrics.get("max_dd", 0) < -0.45 or sanity_metrics.get("sharpe", 0) < -0.2):
                         logger.info("Sanity check failed", id=cand.id)
                         blended = -1.0

                    if blended > 0:
                        instrument_candidates_scores.append({
                            "candidate": cand,
                            "score": blended,
                            "metrics_5m": cand_metrics.get("5m"),
                            "metrics_15m": cand_metrics.get("15m"),
                            "sanity_metrics": sanity_metrics
                        })

            # Rank
            instrument_candidates_scores.sort(key=lambda x: x["score"], reverse=True)
            leaderboards[instrument] = instrument_candidates_scores

            # Promotion
            if instrument_candidates_scores and not self.fast_mode:
                top_challenger = instrument_candidates_scores[0]
                current_champ = self.store.load_champion(instrument)

                metrics_to_check = top_challenger.get("metrics_15m") or top_challenger.get("metrics_5m")

                if self.store.check_promotion(current_champ, metrics_to_check, top_challenger["score"]):
                    self.store.save_champion(
                        instrument,
                        top_challenger["candidate"],
                        metrics_to_check,
                        top_challenger["score"]
                    )

        # 4. Generate Reports
        self._generate_report(leaderboards)

        # 5. Live Signal
        # Only if FULL mode and proper time?
        # Actually SignalPublisher checks market hours.
        if not self.fast_mode:
            self.publisher.run()

        logger.info("Hourly Run Completed")

    def _run_folds(self, candidate, data, k):
        """Run k-fold backtest (sequential chunks)"""
        n = len(data)
        if n < k * 100: # Min bars check
            return []

        chunk_size = n // k
        metrics_list = []

        for i in range(k):
            start = i * chunk_size
            end = start + chunk_size
            # Overlap slightly? No, sequential is fine for stability check.
            chunk = data.iloc[start:end]

            res = self.engine.run(candidate, chunk)
            if res.get("metrics"):
                metrics_list.append(res["metrics"])

        return metrics_list

    def get_symbol(self, instrument):
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            imap = yaml.safe_load(f)
        return imap["research"][instrument]

    def _save_candidates(self, candidates):
        # Save generated candidates
        pass # Optional, maybe just log

    def _generate_report(self, leaderboards):
        report_path = self.results_dir / "leaderboard.md"
        with open(report_path, "w") as f:
            f.write(f"# Strategy Foundry Run {self.run_ts}\n\n")

            for inst, items in leaderboards.items():
                f.write(f"## {inst}\n")
                f.write("| Rank | ID | Score | Sharpe (5m/15m) | MaxDD (5m/15m) | Trades |\n")
                f.write("|---|---|---|---|---|---|\n")
                for i, item in enumerate(items[:10]):
                    m5 = item.get("metrics_5m", {}) or {}
                    m15 = item.get("metrics_15m", {}) or {}
                    f.write(f"| {i+1} | {item['candidate'].id} | {item['score']:.2f} | "
                            f"{m5.get('sharpe',0):.2f}/{m15.get('sharpe',0):.2f} | "
                            f"{m5.get('max_dd',0):.2f}/{m15.get('max_dd',0):.2f} | "
                            f"{m5.get('total_trades',0)}/{m15.get('total_trades',0)} |\n")
                f.write("\n")

if __name__ == "__main__":
    HourlyRunner().run()
