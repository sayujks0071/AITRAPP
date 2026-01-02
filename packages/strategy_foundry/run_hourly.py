import os
import yaml
import json
import pandas as pd
import structlog
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.selection.ranker import StrategyRanker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec

logger = structlog.get_logger(__name__)

class FoundryRunner:
    def __init__(self):
        self.loader = DataLoader()
        self.generator = StrategyGenerator()
        self.ranker = StrategyRanker()
        self.store = ChampionStore()
        self.publisher = SignalPublisher()

        self.fast_mode = os.environ.get("FAST_MODE", "0") == "1"
        self.config = self.loader.config

        # Override config based on mode
        if self.fast_mode:
            logger.info("Running in FAST_MODE")
            self.count = self.config["generation"]["fast_mode_count"]
            self.folds = self.config["generation"]["fast_mode_folds"]
        else:
            self.count = self.config["generation"]["candidates_count"]
            self.folds = self.config["generation"]["folds"]

        self.results_dir = Path("packages/strategy_foundry/results/runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        instruments = self.loader.instrument_map["research"].keys()
        timeframes = self.config["backtest"]["timeframes"]

        for instrument in instruments:
            for tf in timeframes:
                try:
                    self._process_instrument_timeframe(instrument, tf)
                except Exception as e:
                    logger.error("Failed to process", instrument=instrument, timeframe=tf, error=str(e))

    def _process_instrument_timeframe(self, instrument: str, timeframe: str):
        logger.info(f"Processing {instrument} {timeframe}")

        # 1. Load Data
        data = self.loader.get_ohlcv(instrument, timeframe)
        if data is None or len(data) < 200:
            logger.warning("Insufficient data", instrument=instrument)
            return

        # 2. Generate Candidates
        candidates_specs = self.generator.generate(self.count, instrument, timeframe)

        # 3. Evaluate
        evaluator = WalkForwardEvaluator(data, folds=self.folds)
        results = []

        for spec in candidates_specs:
            try:
                ev_res = evaluator.evaluate(spec)
                if "error" not in ev_res:
                    candidate = {
                        "id": spec.id,
                        "spec": spec, # object
                        "spec_dict": spec.__dict__, # for json (needs serialization helper)
                        "evaluation": ev_res
                    }
                    results.append(candidate)
            except Exception as e:
                logger.warning("Evaluation failed", id=spec.id, error=str(e))

        # 4. Rank
        ranked = self.ranker.rank(results)

        # 5. Sanity Check (Top 10)
        # Load 1D data
        data_1d = self.loader.get_ohlcv(instrument, "1d")
        passed_sanity = []

        for cand in ranked[:10]:
            if data_1d is not None and len(data_1d) > 200:
                # Run backtest on 1D
                engine_1d = BacktestEngine(data_1d)
                res_1d = engine_1d.run(cand["spec"])
                metrics_1d = res_1d["metrics"]

                # Check for catastrophic failure
                if metrics_1d["sharpe_ratio"] < -0.2 or metrics_1d["max_drawdown"] > 0.45:
                    logger.info("Candidate failed sanity check", id=cand["id"])
                    cand["sanity_check"] = "FAIL"
                else:
                    cand["sanity_check"] = "PASS"
                    passed_sanity.append(cand)
            else:
                # No 1D data, skip check
                passed_sanity.append(cand)

        # 6. Save Results
        self._save_results(ranked, instrument, timeframe)

        # 7. Promotion (only in full mode?)
        # Prompt: "FAST_MODE... DO NOT promote champions"
        if not self.fast_mode and passed_sanity:
            challenger = passed_sanity[0]
            self._attempt_promotion(challenger, timeframe)

        # 8. Publish Signal (if current champion exists)
        # Load current champion
        champion = self.store.load_champion(timeframe)
        if champion:
            self.publisher.publish(champion, data, self.loader.instrument_map)
        else:
             # Try publishing signal for new challenger if we just promoted it?
             # Or if we didn't promote but one exists.
             # If no champion, we can't publish.
             pass

    def _save_results(self, ranked: List[Dict], instrument: str, timeframe: str):
        # Convert to DF for CSV
        rows = []
        for r in ranked:
            row = {
                "id": r["id"],
                "score": r["score"],
                "sharpe": r["evaluation"]["avg_sharpe"],
                "dd": r["evaluation"]["avg_max_drawdown"],
                "trades": r["evaluation"]["total_trades"],
                "sanity": r.get("sanity_check", "N/A"),
                "rule_summary": str([b.type for b in r["spec"].blocks])
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(self.results_dir / f"leaderboard_{instrument}_{timeframe}.csv", index=False)

        # Markdown
        with open(self.results_dir / f"leaderboard_{instrument}_{timeframe}.md", "w") as f:
            f.write(df.to_markdown())

    def _attempt_promotion(self, challenger: Dict, timeframe: str):
        current = self.store.load_champion(timeframe)

        # Live Eligibility Gate
        eval = challenger["evaluation"]
        gate_config = self.config["live"]
        if (eval["avg_sharpe"] < gate_config["required_sharpe"] or
            eval["avg_max_drawdown"] > (gate_config["max_allowed_dd"] / 100.0)):
            logger.info("Challenger failed live eligibility", id=challenger["id"])
            return

        should_promote = False
        if not current:
            should_promote = True
        else:
            # Compare
            score_imp = (challenger["score"] - current["score"]) / abs(current["score"]) if current["score"] != 0 else 1.0
            dd_red = (current["evaluation"]["avg_max_drawdown"] - challenger["evaluation"]["avg_max_drawdown"])

            if score_imp >= 0.10: # 10% improvement
                should_promote = True
            elif dd_red >= 0.05: # 5% DD reduction
                should_promote = True

        if should_promote:
            # Serialize spec properly
            # challenger['spec'] is an object. Convert to dict for storage.
            from dataclasses import asdict
            champ_data = {
                "id": challenger["id"],
                "blocks": [asdict(b) for b in challenger["spec"].blocks],
                "timeframe": challenger["spec"].timeframe,
                "instrument": challenger["spec"].instrument,
                "score": challenger["score"],
                "evaluation": challenger["evaluation"]
            }
            self.store.save_champion(champ_data, timeframe)

if __name__ == "__main__":
    runner = FoundryRunner()
    runner.run()
