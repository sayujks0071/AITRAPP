"""
Strategy Foundry - Hourly Runner.
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import structlog
from typing import List, Dict, Any

from packages.strategy_foundry.data.loader import fetch_data
from packages.strategy_foundry.factory.grammar import generate_candidate
from packages.strategy_foundry.backtest.walkforward import WalkForwardAnalyst
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import rank_candidates
from packages.strategy_foundry.selection.promote import compare_and_promote, load_champion
from packages.strategy_foundry.live.signal_publisher import publish_signal
from packages.strategy_foundry.backtest.engine import BacktestEngine

logger = structlog.get_logger(__name__)

def run():
    # 1. Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"packages/strategy_foundry/results/runs/{timestamp}")
    results_dir.mkdir(parents=True, exist_ok=True)

    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    n_candidates = 10 if fast_mode else 50
    n_folds = 2 if fast_mode else 4

    logger.info("Starting Strategy Foundry Run", fast_mode=fast_mode, timestamp=timestamp)

    # 2. Data
    # NIFTY only for now as primary
    symbol = "NIFTY"
    try:
        df = fetch_data(symbol)
    except Exception as e:
        logger.error("Failed to fetch data", error=str(e))
        sys.exit(1)

    # 3. Generate & Evaluate Candidates
    candidates = []

    for _ in range(n_candidates):
        config = generate_candidate()

        # Walk Forward
        wf = WalkForwardAnalyst(df, n_folds=n_folds)
        res = wf.run(config)

        if res["valid"]:
             # Sanity Check
            if check_sanity(res):
                candidates.append({
                    "id": config["id"],
                    "config": config,
                    "metrics": res,
                    "rule_summary": "" # TODO
                })

    logger.info("Candidates generated", count=len(candidates), valid=len(candidates))

    # 4. Rank
    ranked = rank_candidates(candidates)

    # Save Results
    # Simplify for JSON
    serializable_ranked = []
    for c in ranked:
        # Metrics has 'folds' with DataFrames, need to strip or summarize
        # We need to serialize carefully.
        # Actually, res['trades'] is a DataFrame.
        # Let's drop trades and just keep summary metrics for the list.
        summary = c.copy()
        summary["metrics"] = c["metrics"].copy()

        # Safe pop for top level trades DF in metrics dict (from WalkForward)
        if "trades" in summary["metrics"]:
             summary["metrics"].pop("trades")

        # Remove trades from folds
        folds = []
        for f in summary["metrics"]["metrics"].get("folds", []):
            f_clean = f.copy()
            # compute_metrics returns dict of floats, no DF usually, but check
            if "trades" in f_clean and isinstance(f_clean["trades"], pd.DataFrame):
                 f_clean.pop("trades")
            folds.append(f_clean)
        summary["metrics"]["metrics"]["folds"] = folds
        serializable_ranked.append(summary)

    with open(results_dir / "candidates.json", 'w') as f:
        json.dump(serializable_ranked, f, indent=2)

    # Leaderboard
    leaderboard_file = Path("packages/strategy_foundry/results/leaderboard.md")
    with open(leaderboard_file, "w") as f:
        f.write("# Strategy Leaderboard\n\n")
        f.write("| Rank | ID | Score | Sharpe | CAGR | MaxDD |\n")
        f.write("|---|---|---|---|---|---|\n")
        for i, c in enumerate(serializable_ranked[:20]):
            m = c["metrics"]["metrics"]
            f.write(f"| {i+1} | {c['id'][:8]} | {c.get('score',0):.2f} | {m.get('sharpe',0):.2f} | {m.get('cagr',0):.2f} | {m.get('max_drawdown',0):.2f} |\n")

    # 5. Champion Promotion
    if serializable_ranked:
        best = serializable_ranked[0]
        # Use serializable version for storage
        compare_and_promote(best)

    # 6. Live Signal Generation
    champion = load_champion()
    if champion:
        engine = BacktestEngine(df)
        res = engine.run(champion["config"])
        is_open = res.get("is_open", False)

        signal = 1 if is_open else 0

        publish_signal(
            champion=champion,
            signal=signal,
            instrument=symbol,
            reason="Champion Signal"
        )

if __name__ == "__main__":
    run()
