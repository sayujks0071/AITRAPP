import os
import sys
import time
import pandas as pd
import structlog
from datetime import datetime
import pytz

from packages.strategy_foundry.data.loader import get_data
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.registry import CandidateRegistry
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.selection.ranker import score_candidate
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.live.signal_publisher import publish_signal

logger = structlog.get_logger(__name__)

RESULTS_DIR = "packages/strategy_foundry/results"
LEADERBOARD_CSV = os.path.join(RESULTS_DIR, "leaderboard.csv")
LEADERBOARD_MD = os.path.join(RESULTS_DIR, "leaderboard.md")

def main():
    # 1. Config
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    n_candidates = 10 if fast_mode else 50
    symbols = ["NIFTY", "SENSEX"]

    run_ts = int(time.time())
    run_dir = os.path.join(RESULTS_DIR, "runs", str(run_ts))
    os.makedirs(run_dir, exist_ok=True)

    logger.info("Starting Hourly Run", fast_mode=fast_mode, run_dir=run_dir)

    # 2. Update Data
    data_map = {}
    for sym in symbols:
        try:
            df = get_data(sym, lookback_days=2000) # Ensure enough history
            if not df.empty:
                data_map[sym] = df
            else:
                logger.warning(f"Data for {sym} is empty")
        except Exception as e:
            logger.error(f"Failed to load data for {sym}", error=str(e))

    if not data_map:
        logger.error("No data available, aborting")
        return

    # 3. Generate Candidates
    generator = StrategyGenerator()
    candidates = generator.generate_candidates(n=n_candidates)

    registry = CandidateRegistry(run_dir)
    registry.save_candidates(candidates)
    logger.info(f"Generated {len(candidates)} candidates")

    # 4. Evaluate (Walk-Forward / OOS)
    evaluator = WalkForwardEvaluator()
    results = []

    # Helper to append to leaderboard
    leaderboard_rows = []

    for cand in candidates:
        # Evaluate on NIFTY primarily for ranking, or aggregate?
        # Plan says "Output per candidate per instrument".
        # Ranking usually on primary instrument or average.
        # Let's rank on NIFTY.

        sym = "NIFTY"
        if sym not in data_map: continue

        df = data_map[sym]
        metrics = evaluator.evaluate(df, cand)

        score = score_candidate(metrics)

        res = {
            "run_ts": run_ts,
            "id": cand.id,
            "symbol": sym,
            "score": score,
            "metrics": metrics,
            "summary": cand.summary
        }
        results.append((cand, metrics, score))

        # Flatten for CSV
        row = {
            "run_ts": run_ts,
            "id": cand.id,
            "symbol": sym,
            "score": round(score, 4),
            "cagr": round(metrics.get('cagr', 0), 4),
            "sharpe": round(metrics.get('sharpe', 0), 4),
            "max_dd": round(metrics.get('max_drawdown', 0), 4),
            "trades": metrics.get('trades', 0),
            "summary": cand.summary
        }
        leaderboard_rows.append(row)

    # Save Run Metrics
    metrics_df = pd.DataFrame(leaderboard_rows)
    metrics_df.to_csv(os.path.join(run_dir, "metrics.csv"), index=False)

    # 5. Update Global Leaderboard
    if os.path.exists(LEADERBOARD_CSV):
        global_df = pd.read_csv(LEADERBOARD_CSV)
        global_df = pd.concat([global_df, metrics_df], ignore_index=True)
    else:
        global_df = metrics_df

    # Deduplicate by ID? No, same ID might be re-evaluated later with more data.
    # But for leaderboard we might want unique strategies.
    # Let's keep history.
    global_df.to_csv(LEADERBOARD_CSV, index=False)

    # Generate MD Leaderboard (Top 20 Unique by Score)
    top_20 = global_df.sort_values("score", ascending=False).drop_duplicates("id").head(20)
    with open(LEADERBOARD_MD, "w") as f:
        f.write("# Strategy Foundry Leaderboard\n\n")
        f.write(f"Last Updated: {datetime.now(pytz.timezone('Asia/Kolkata')).isoformat()}\n\n")
        f.write(top_20.to_markdown(index=False))

    # 6. Champion Selection
    # Find best in CURRENT run
    best_cand, best_metrics, best_score = max(results, key=lambda x: x[2]) if results else (None, {}, -float('inf'))

    if best_cand:
        store = ChampionStore(os.path.join(RESULTS_DIR, "champions"))
        current_meta = store.load_current_metadata()
        current_metrics = current_meta.get('metrics')

        if should_promote(best_cand, best_metrics, current_metrics):
            logger.info("Promoting new champion", id=best_cand.id, score=best_score)
            store.promote_new_champion(best_cand, best_metrics, best_score)
        else:
            logger.info("No promotion", best_score=best_score, current_score=current_meta.get('score'))

    # 7. Publish Live Signal
    publish_signal()

if __name__ == "__main__":
    main()
