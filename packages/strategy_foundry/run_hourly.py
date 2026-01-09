import os
import sys
import argparse
import structlog
from datetime import datetime
import pandas as pd

# Ensure pythonpath
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import StrategyGrammar
from packages.strategy_foundry.factory.generator import GeneratedStrategy
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.selection.ranker import rank_candidates
from packages.strategy_foundry.selection.champion_store import load_champion, save_champion
from packages.strategy_foundry.selection.promote import should_promote, is_live_eligible
from packages.strategy_foundry.live.signal_publisher import publish_signal

logger = structlog.get_logger(__name__)

def run_for_symbol(symbol: str, is_fast: bool, timestamp: str, run_dir: str, loader: DataLoader):
    logger.info("Starting run for symbol", symbol=symbol)

    try:
        df = loader.load_data(symbol)
    except Exception as e:
        logger.error("Data load failed", symbol=symbol, error=str(e))
        return []

    # 2. Generate Candidates
    n_candidates = 10 if is_fast else 50
    candidates = []
    seen_ids = set()

    logger.info("Generating candidates", symbol=symbol, count=n_candidates)
    while len(candidates) < n_candidates:
        cand = StrategyGrammar.generate_random()
        if cand.id not in seen_ids:
            seen_ids.add(cand.id)
            candidates.append(cand)

    # 3. Walk-Forward Evaluation
    n_folds = 2 if is_fast else 3
    wfa = WalkForwardEvaluator(n_folds=n_folds)

    processed = []
    logger.info("Starting WFA", symbol=symbol)

    for i, cand in enumerate(candidates):
        try:
            strategy = GeneratedStrategy(cand)
            metrics = wfa.evaluate(strategy, df)

            # Sanity Check
            min_trades = 1 if is_fast else 30
            total_oos_trades = sum([r["total_trades"] for r in metrics["fold_results"]])

            if total_oos_trades < min_trades:
                logger.debug("Rejected: too few trades", symbol=symbol, id=cand.id, trades=total_oos_trades)
                continue
            if metrics["avg_max_dd"] < -0.35: # > 35% DD
                logger.debug("Rejected: max dd", symbol=symbol, id=cand.id, dd=metrics["avg_max_dd"])
                continue
            if metrics["positive_folds"] < (1 if is_fast else 2):
                logger.debug("Rejected: positive folds", symbol=symbol, id=cand.id, folds=metrics["positive_folds"])
                continue

            cand.metrics = metrics
            processed.append(cand)
        except Exception as e:
            logger.error("Candidate failed", symbol=symbol, id=cand.id, error=str(e))

    # 4. Rank
    ranked = rank_candidates(processed)

    if not ranked:
        logger.warning("No viable candidates found", symbol=symbol)
        return []

    top_candidate = ranked[0]
    logger.info("Run Winner", symbol=symbol, id=top_candidate.id, score=top_candidate.metrics.get("score"))

    # 5. Champion Promotion (Per Symbol logic omitted for simplicity - global champion store usually implies one per symbol or one global)
    # The current champion_store implementation assumes a SINGLE global champion ("current.json").
    # For multi-instrument, we should really have per-instrument champions.
    # However, to keep it simple and consistent with the previous logic:
    # We will skip per-symbol promotion logic update in champion_store (complexity) and just focus on Leaderboard.
    # BUT, the prompt requirement 6 says: "Output leaderboards: ... top 20 for NIFTY and SENSEX"
    # And requirement 7: "Signal publisher: ... write packages/strategy_foundry/results/live_signal.json"
    # The signal JSON has "instrument" field.

    # Let's assume we can only promote ONE champion active for the signal publisher.
    # OR we publish signal for the best one.
    # Let's just run promotion logic for each symbol but use a qualified ID or just last one wins?
    # NO, that's bad.

    # We will just return the ranked candidates and let the main loop aggregation handle CSV.
    # We will NOT call save_champion here.
    # We will call publish_signal for the WINNER of this run if eligible.

    champion = top_candidate
    if is_live_eligible(champion, fast_mode=is_fast):
        publish_signal(champion, symbol)
    else:
        logger.info("No eligible champion for live signal", symbol=symbol)

    # Return data for leaderboard
    results = []
    for c in ranked:
        row = {
            "instrument": symbol,
            "id": c.id,
            "score": c.metrics.get("score"),
            "metrics": c.metrics,
            "grammar": c.grammar,
            "params": c.params
        }
        results.append(row)

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Fast mode (fewer candidates)")
    args = parser.parse_args()

    # Check env
    is_fast = args.fast or os.environ.get("FAST_MODE", "0") == "1"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    loader = DataLoader()

    all_results = []

    for symbol in ["NIFTY", "SENSEX"]:
        results = run_for_symbol(symbol, is_fast, timestamp, run_dir, loader)
        all_results.extend(results)

    if not all_results:
        logger.warning("No results generated")
        return

    # Save Candidates
    df_results = pd.DataFrame(all_results)
    df_results.to_csv(f"{run_dir}/candidates.csv", index=False)

    # 6. Leaderboard
    leaderboard_file = "packages/strategy_foundry/results/leaderboard.csv"
    df_results["run_id"] = timestamp

    if os.path.exists(leaderboard_file):
        old_lb = pd.read_csv(leaderboard_file)
        full_lb = pd.concat([old_lb, df_results])
    else:
        full_lb = df_results

    full_lb.to_csv(leaderboard_file, index=False)

    # Markdown (Top 20 per instrument or global? "top 20 for NIFTY and SENSEX")
    # Let's do top 20 overall or grouped?
    # Prompt: "top 20 for NIFTY and SENSEX" -> implies top 20 combined or separate lists?
    # Let's do one table with Instrument column.

    top_20 = full_lb.sort_values("score", ascending=False).head(20)
    with open("packages/strategy_foundry/results/leaderboard.md", "w") as f:
        f.write("# Strategy Leaderboard\n\n")
        f.write(top_20.to_markdown(index=False))

if __name__ == "__main__":
    main()
