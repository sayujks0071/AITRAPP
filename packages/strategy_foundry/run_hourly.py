"""Strategy Foundry - Hourly Runner"""
import os
import yaml
import logging
import pytz
import pandas as pd
from datetime import datetime
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategyFoundry")

# Imports
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardValidator
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import rank_candidates, calculate_score
from packages.strategy_foundry.selection.promote import can_promote
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import publish_signal
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.factory.grammar import StrategyGrammar

# Config Paths
CONFIG_DIR = "packages/strategy_foundry/configs"
BACKTEST_CONFIG = os.path.join(CONFIG_DIR, "backtest.yaml")
INSTRUMENT_MAP = os.path.join(CONFIG_DIR, "instrument_map.yaml")
RESULTS_DIR = "packages/strategy_foundry/results"

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def run():
    logger.info("Starting Strategy Foundry Hourly Run")

    # 1. Load Configs
    bt_config = load_config(BACKTEST_CONFIG)
    inst_map = load_config(INSTRUMENT_MAP)

    # 2. Update Data
    loader = DataLoader(cache_dir=bt_config["data"]["cache_dir"])

    # We focus on NIFTY 50 (^NSEI) as primary for MVP champion selection
    primary_symbol = "^NSEI"
    try:
        df = loader.get_history(primary_symbol, days=bt_config["data"]["history_days"])
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # 3. Generate Candidates
    gen_config = bt_config["generation"]
    # Adjust count for FAST_MODE (CI)
    candidates_count = gen_config["candidates_per_hour"]
    if os.environ.get("FAST_MODE", "false").lower() == "true":
        candidates_count = 5
        logger.info("Running in FAST_MODE (5 candidates)")

    generator = StrategyGenerator()
    candidates = generator.generate_candidates(n=candidates_count)

    # 4. Backtest & Evaluate
    evaluated_candidates = []

    engine = BacktestEngine(
        df,
        initial_capital=bt_config["backtest"]["initial_capital"],
        costs_bps=bt_config["costs"]["default_bps"],
        slippage_bps=bt_config["costs"]["slippage_bps"]
    )

    validator = WalkForwardValidator(engine, folds=5)

    for cand in candidates:
        try:
            # Full Backtest
            bt_res = engine.run(cand)
            metrics = bt_res["metrics"]

            # Walk Forward
            wf_res = validator.validate(cand)

            # Combine results
            cand["metrics"] = metrics
            cand["walkforward"] = wf_res

            # Sanity Check
            if check_sanity(metrics, bt_config["constraints"]):
                evaluated_candidates.append(cand)

        except Exception as e:
            logger.warning(f"Candidate failed: {e}")
            continue

    # 5. Rank & Select Champion
    ranked = rank_candidates(evaluated_candidates)

    if not ranked:
        logger.warning("No viable candidates found this run.")
        return

    top_candidate = ranked[0]
    logger.info(f"Top Candidate Score: {top_candidate.get('score'):.2f}")

    # 6. Champion Logic
    store = ChampionStore()
    current_champion = store.load_champion()

    new_champion = None

    if current_champion:
        # Re-evaluate current champion with latest data
        logger.info("Re-evaluating current champion with latest data...")
        try:
            # Re-run backtest on latest data
            bt_res = engine.run(current_champion)
            updated_metrics = bt_res["metrics"]
            
            # Re-run walk-forward validation
            wf_res = validator.validate(current_champion)
            
            # Re-calculate score with updated metrics and walkforward results
            updated_score = calculate_score(updated_metrics, wf_res)
            
            # Update champion fields atomically after all computations succeed
            current_champion["metrics"] = updated_metrics
            current_champion["walkforward"] = wf_res
            current_champion["score"] = updated_score
            
            logger.info(f"Current Champion re-evaluated. Score: {current_champion.get('score'):.2f}")
        except Exception as e:
            logger.warning(f"Failed to re-evaluate current champion: {e}. Using stored metrics.")
        
        # Compare
        curr_score = current_champion.get("score", 0)
        new_score = top_candidate.get("score", 0)

        # Must beat by margin (configurable)
        promotion_margin = bt_config.get("selection", {}).get("promotion_margin", 1.1)
        if new_score > curr_score * promotion_margin:
            logger.info(f"New Champion Found! (Score Improvement: {new_score:.2f} > {curr_score:.2f} * {promotion_margin})")
            new_champion = top_candidate
        else:
            logger.info(f"Current Champion remains. (New: {new_score:.2f} vs Current: {curr_score:.2f} * {promotion_margin} = {curr_score * promotion_margin:.2f})")
            new_champion = current_champion
    else:
        logger.info("First Champion initialized.")
        new_champion = top_candidate

    store.save_champion(new_champion)

    # 7. Reporting
    # Save Leaderboard
    lb_path = os.path.join(RESULTS_DIR, "leaderboard.csv")
    lb_data = []
    for r in ranked[:20]:
        row = {
            "id": r["id"],
            "score": r.get("score"),
            "sharpe": r["metrics"].get("sharpe"),
            "max_dd": r["metrics"].get("max_dd"),
            "cagr": r["metrics"].get("cagr"),
            "logic": r["logic_type"]
        }
        lb_data.append(row)
    pd.DataFrame(lb_data).to_csv(lb_path, index=False)

    # Save Leaderboard MD
    lb_md_path = os.path.join(RESULTS_DIR, "leaderboard.md")
    with open(lb_md_path, "w") as f:
        f.write("# Strategy Leaderboard\n\n")
        f.write(f"Updated: {datetime.now(pytz.timezone('Asia/Kolkata')).isoformat()}\n\n")
        f.write("| Rank | ID | Score | Sharpe | MaxDD | CAGR | Logic |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(ranked[:20]):
            m = r["metrics"]
            f.write(f"| {i+1} | {r['id'][:8]} | {r.get('score'):.2f} | {m.get('sharpe'):.2f} | {m.get('max_dd'):.2f} | {m.get('cagr'):.2%} | {r['logic_type']} |\n")

    # 8. Live Signal Publishing
    # Check Market Hours
    mh = MarketHoursAdapter()
    if not mh.is_market_open():
        logger.info("Market Closed. Skipping signal publish.")
        return

    # Check Promotion
    is_promotable, reasons = can_promote(new_champion)
    if not is_promotable:
        logger.info(f"Champion not promotable for Live: {reasons}")
        return

    # Generate Signal for NOW
    # We need to run the champion on the latest data one last time to get the signal
    # Data loader already fetched latest available.
    grammar = StrategyGrammar(new_champion)
    signals = grammar.generate_signals(df)

    # Signal at last bar (today's close/latest).
    # Since we trade at NEXT OPEN, this signal is for tomorrow/next session?
    # Or if we run intraday, it's for now?
    # Prompt: "Live signal publisher that only emits signals (JSON)... Market hours check: NSE normal session 09:15–15:30 IST"
    # "Enforce 'no lookahead': signals generated using past/closed bars only."

    # If we run at e.g. 10:00 AM, we have data up to yesterday Close?
    # Or if data loader fetches intraday, we have up to now.
    # Our simple Yahoo loader fetches Daily bars. So we only have yesterday's Close.
    # So the signal generated is based on Yesterday Close.
    # Action: Buy/Sell at Today Open (which passed at 9:15).
    # If we run at 10:00 AM, we are effectively telling the system "You should be Long/Short based on Yesterday".
    # This is correct for a Daily strategy running in Live. It maintains position.

    latest_signal = int(signals.iloc[-1])

    # Publish
    proxy = inst_map[primary_symbol]["proxy_symbol"]
    publish_signal(new_champion, latest_signal, primary_symbol, proxy, reason="Hourly Update")

if __name__ == "__main__":
    run()
