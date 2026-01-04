import os
import sys
import structlog
from datetime import datetime
from pathlib import Path
import pandas as pd
import pytz

# Add repo root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import load_instrument_data
from packages.strategy_foundry.factory.generator import generate_candidates
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import sanity_check
from packages.strategy_foundry.selection.ranker import score_strategy
from packages.strategy_foundry.selection.promote import promote_if_better
from packages.strategy_foundry.live.signal_publisher import publish_live_signal

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# Config
SYMBOLS = ["NIFTY", "SENSEX"]
FAST_MODE = os.getenv("FAST_MODE", "0") == "1"

def run():
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"packages/strategy_foundry/results/runs/{run_ts}")
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Hourly Run", fast_mode=FAST_MODE, run_dir=str(run_dir))

    for symbol in SYMBOLS:
        try:
            logger.info("Processing Symbol", symbol=symbol)

            # 1. Load Data
            df = load_instrument_data(symbol)
            if df.empty:
                logger.error("No data", symbol=symbol)
                continue

            # 2. Generate Candidates
            n_candidates = 10 if FAST_MODE else 50
            candidates = generate_candidates(n_candidates)
            logger.info("Generated candidates", count=len(candidates))

            # 3. Evaluate
            n_folds = 2 if FAST_MODE else 4
            evaluator = WalkForwardEvaluator(n_folds=n_folds)

            results = []

            for strategy in candidates:
                metrics = evaluator.evaluate(strategy, df)

                if metrics["valid"]:
                    # Sanity Check
                    if sanity_check(metrics, FAST_MODE):
                        # Score
                        score = score_strategy(metrics)

                        result_entry = {
                            "id": strategy.id,
                            "config": strategy.config,
                            "metrics": {
                                "avg_sharpe": metrics["avg_sharpe"],
                                "avg_cagr": metrics["avg_cagr"],
                                "worst_drawdown": metrics["worst_drawdown"],
                                "total_trades": metrics["total_trades"],
                                "positive_folds": metrics["positive_folds"],
                                "sharpe_dispersion": metrics["sharpe_dispersion"]
                            },
                            "score": score
                        }
                        results.append(result_entry)

            logger.info("Evaluation complete", passed_sanity=len(results))

            # 4. Rank and Promote
            if results:
                results.sort(key=lambda x: x["score"], reverse=True)

                # Save candidates to run artifact
                with open(run_dir / f"candidates_{symbol}.json", "w") as f:
                    import json
                    json.dump(results, f, indent=2)

                top_candidate = results[0]
                promote_if_better(top_candidate, symbol)

            # 5. Live Signal
            # Check market hours?
            # Logic: If market is open (Mon-Fri 9:15-15:30 IST).
            # We can use a simple check here or delegate to publisher.
            # Publisher will just write "SKIPPED" if we don't call it, or we call it and it checks.
            # For simplicity, let's just call it. It generates signal based on latest data.
            publish_live_signal(symbol, df)

        except Exception as e:
            logger.error("Run failed for symbol", symbol=symbol, error=str(e))
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run()
