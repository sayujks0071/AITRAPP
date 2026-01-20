"""Main orchestration script"""
import os
import sys
import argparse
import pandas as pd
import structlog
from datetime import datetime
import pytz
import yaml

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.selection.ranker import rank_candidates
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.backtest.sanity import run_sanity_check
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate

# Configure logger
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

def load_config() -> dict:
    try:
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode")
    args = parser.parse_args()

    # Check Env
    is_fast = args.fast or os.environ.get("FAST_MODE") == "1"

    # Configs
    timeframes = ["15m", "5m"]
    n_candidates = 15 if is_fast else 80
    n_folds = 2 if is_fast else 4

    logger.info("Starting Strategy Foundry", mode="FAST" if is_fast else "FULL")

    # 1. Load Data
    loader = DataLoader()
    config = load_config()
    symbol = config.get("research", {}).get("NIFTY", "^NSEI")

    # Load Intraday
    data_map = {}
    for tf in timeframes:
        df = loader.get_data(symbol, tf)
        if df is None or df.empty:
            logger.error("No data found", symbol=symbol, timeframe=tf)
            sys.exit(1)
        data_map[tf] = df

    # Load Daily for Sanity
    daily_df = loader.get_data(symbol, "1d")

    # 2. Generate Candidates
    generator = StrategyGenerator()
    candidates = generator.generate(count=n_candidates, timeframes=timeframes)

    logger.info("Generated candidates", count=len(candidates))

    # 3. Backtest & Walk-forward
    wf = WalkForward(n_folds=n_folds)

    candidates_with_metrics = []

    for cand in candidates:
        df = data_map[cand.timeframe]
        try:
            res = wf.evaluate(cand, df)
            candidates_with_metrics.append((cand, res))
        except Exception as e:
            logger.error("Candidate failed", id=cand.get_id(), error=str(e))

    # 4. Rank
    ranked_df = rank_candidates(candidates_with_metrics)

    # Save Run Results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{ts}"
    os.makedirs(run_dir, exist_ok=True)

    store = ChampionStore()

    if not ranked_df.empty:
        ranked_df.drop(columns=["candidate", "metrics"]).to_csv(f"{run_dir}/leaderboard.csv", index=False)
        logger.info("Ranking complete", top_score=ranked_df.iloc[0]["score"])

        # 5. Sanity Check Top 10
        top_candidates = ranked_df.head(10)
        valid_candidates = []

        for _, row in top_candidates.iterrows():
            cand = row["candidate"]
            metrics = row["metrics"]

            # Run 1D Sanity
            sanity = run_sanity_check(cand, daily_df)
            if sanity["passed"]:
                valid_candidates.append((cand, metrics, row["score"]))
            else:
                logger.info("Sanity failed", id=cand.get_id(), reason=sanity["reason"])

        # 6. Champion Selection (Only in FULL mode or if forced)
        if valid_candidates:
            top_cand, top_metrics, top_score = valid_candidates[0]

            # Live Eligibility Check
            is_eligible = True

            if top_metrics.get("avg_sharpe", 0) < 1.2:
                is_eligible = False
            if top_metrics.get("max_dd", -1) < -0.20:
                is_eligible = False
            if top_metrics.get("positive_folds", 0) < (3 if not is_fast else 1):
                is_eligible = False

            if is_eligible and not is_fast:
                if store.should_promote(top_score, top_metrics.get("max_dd", 0), top_metrics.get("avg_sharpe", 0)):
                    logger.info("New Champion Promoted", id=top_cand.get_id())
                    store.save_champion(top_cand.to_dict(), top_metrics, top_score)
                else:
                    logger.info("Champion retained")
            else:
                 logger.info("Top candidate not eligible for promotion", eligible=is_eligible)

        else:
             logger.warning("No valid candidates after sanity check")
    else:
        logger.warning("No candidates ranked")

    # 7. Publish Live Signal (INDEPENDENT of current run success)
    # Use current champion from store
    current_champion_data = store.load_current()
    publisher = SignalPublisher()

    if current_champion_data:
        # We need to run the champion on LATEST data to get signal
        c_data = current_champion_data["candidate"]
        champ_cand = StrategyCandidate.from_dict(c_data)

        # Run on latest data (full dataset)
        tf = champ_cand.timeframe
        df_live = data_map.get(tf)

        if df_live is not None:
            engine = BacktestEngine(df_live)
            res = engine.run(champ_cand)

            final_position = res.get("final_position", 0)

            publisher.publish(current_champion_data, final_position)
            logger.info("Published live signal", position=final_position)
        else:
            publisher.publish_skipped("Missing data for champion timeframe")
    else:
        publisher.publish_skipped("No champion available")

if __name__ == "__main__":
    main()
