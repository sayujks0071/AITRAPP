import os
import sys
import pandas as pd
from datetime import datetime
import structlog
import pytz

# Add repo root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import get_data
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import walk_forward_evaluate
from packages.strategy_foundry.selection.ranker import calculate_score
from packages.strategy_foundry.selection.champion_store import load_champion, save_champion, reconstruct_strategy
from packages.strategy_foundry.live.signal_publisher import publish_all_signals

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

RESULTS_DIR = "packages/strategy_foundry/results"
RUNS_DIR = os.path.join(RESULTS_DIR, "runs")

def ensure_dirs():
    os.makedirs(RUNS_DIR, exist_ok=True)

def run_hourly():
    ensure_dirs()

    # Mode
    is_fast_mode = os.getenv("FAST_MODE", "0") == "1"

    n_candidates = 10 if is_fast_mode else 50
    folds = 2 if is_fast_mode else 4

    logger.info("Starting Hourly Run", fast_mode=is_fast_mode, candidates=n_candidates)

    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS_DIR, timestamp)
    os.makedirs(run_dir, exist_ok=True)

    instruments = ["NIFTY", "SENSEX"]

    leaderboard_entries = []

    for instrument in instruments:
        logger.info("Processing Instrument", instrument=instrument)

        # 1. Data
        try:
            df = get_data(instrument)
            df = VectorizedIndicators.add_all(df)
        except Exception as e:
            logger.error("Data failed", instrument=instrument, error=str(e))
            continue

        # 2. Generator
        generator = StrategyGenerator()
        candidates = generator.generate_candidates(n_candidates)

        # 3. Evaluate
        engine = BacktestEngine(initial_capital=100000)

        scored_candidates = []

        for cand in candidates:
            res = walk_forward_evaluate(engine, cand, df, folds=folds)

            # Extract Metrics
            metrics = res["metrics"]
            if not metrics:
                continue

            stability = res.get("stability_metric", 1.0)
            passed_folds = res.get("passed_folds", False) # This is boolean
            positive_folds = res.get("positive_folds", 0)

            score = calculate_score(metrics, stability)

            # Store essential info
            cand_info = {
                "id": cand.strategy_id,
                "instrument": instrument,
                "score": score,
                "metrics": metrics,
                "stability": stability,
                "positive_folds": positive_folds,
                "candidate": cand
            }
            scored_candidates.append(cand_info)

        # 4. Rank
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        if not scored_candidates:
            logger.warning("No valid candidates found", instrument=instrument)
            continue

        best_new = scored_candidates[0]

        # 5. Champion Promotion Logic
        current_champ_data = load_champion(instrument)
        promote = False

        if not current_champ_data:
            promote = True
            logger.info("No current champion, promoting best new", instrument=instrument)
        else:
            old_score = current_champ_data.get("score", 0)
            old_metrics = current_champ_data.get("metrics", {})
            old_dd = old_metrics.get("max_drawdown", 1.0)

            new_score = best_new["score"]
            new_dd = best_new["metrics"]["max_drawdown"]

            # Rules:
            # Score >= 1.1 * Old Score
            # OR (Score > Old Score AND DD < 0.8 * Old DD) (Lower DD is better)

            if new_score >= old_score * 1.1:
                promote = True
                logger.info("Promoting: Score Improvement", old=old_score, new=new_score)
            elif new_score > old_score and new_dd < old_dd * 0.8:
                promote = True
                logger.info("Promoting: Risk Improvement", old_dd=old_dd, new_dd=new_dd)

        if promote:
            # Save Champion
            # Need to re-embed passed_folds info if we want to save it?
            # champion_store.save_champion takes (cand, metrics, score, inst)
            # metrics usually just dict.
            save_champion(best_new["candidate"], best_new["metrics"], best_new["score"], instrument)

        # 6. Leaderboard Update
        for sc in scored_candidates[:5]: # Top 5 per instrument
            m = sc["metrics"]
            leaderboard_entries.append({
                "Timestamp": timestamp,
                "Instrument": instrument,
                "ID": sc["id"],
                "Score": round(sc["score"], 2),
                "Sharpe": round(m.get("sharpe", 0), 2),
                "Calmar": round(m.get("calmar", 0), 2),
                "CAGR": round(m.get("cagr", 0), 2),
                "DD": round(m.get("max_drawdown", 0), 2),
                "Trades": m.get("trades", 0),
                "PosFolds": sc["positive_folds"]
            })

    # Save Run Artifacts
    if leaderboard_entries:
        lb_df = pd.DataFrame(leaderboard_entries)
        lb_df.to_csv(os.path.join(run_dir, "leaderboard.csv"), index=False)

        # Global Leaderboard (Append)
        global_lb_path = os.path.join(RESULTS_DIR, "leaderboard.csv")
        lb_df.to_csv(global_lb_path, mode='a', header=not os.path.exists(global_lb_path), index=False)

        # Markdown Leaderboard (Overwrite with Top 20)
        try:
            full_lb = pd.read_csv(global_lb_path)
            full_lb = full_lb.sort_values("Score", ascending=False).head(20)
            md_content = "# Strategy Foundry Leaderboard\n\n"
            md_content += full_lb.to_markdown(index=False)
            with open(os.path.join(RESULTS_DIR, "leaderboard.md"), "w") as f:
                f.write(md_content)
        except Exception as e:
            logger.error("Failed to update markdown leaderboard", error=str(e))

    # Publish Live Signals
    publish_all_signals()

    logger.info("Run Complete")

if __name__ == "__main__":
    run_hourly()
