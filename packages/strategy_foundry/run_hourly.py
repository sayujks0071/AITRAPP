import os
import sys
import structlog
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add repo root to path (needed if running as script from root)
# But clean way is running as module: python -m packages.strategy_foundry.run_hourly
if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.grammar import Strategy, StrategyBlock, EmaCrossBlock, RsiFilterBlock, SupertrendBlock, DonchianBlock
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.adapters.core_costs import CostModel, RiskConfig
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

def reconstruct_strategy(data):
    """Reconstruct Strategy object from dict."""
    blocks = []
    for b_data in data["blocks"]:
        t = b_data["type"]
        p = b_data["params"]
        if t == "EmaCross":
            blocks.append(EmaCrossBlock(p["fast"], p["slow"]))
        elif t == "RsiFilter":
            blocks.append(RsiFilterBlock(p["period"], p["threshold"], p["mode"]))
        elif t == "Supertrend":
            blocks.append(SupertrendBlock(p["period"], p["multiplier"]))
        elif t == "Donchian":
            blocks.append(DonchianBlock(p["period"]))

    risk = data["risk"]
    s = Strategy(blocks, risk["stop_loss_atr"], risk["take_profit_atr"])
    return s

def main():
    logger.info("Starting StrategyFoundry hourly run")

    # 1. Config
    FAST_MODE = os.getenv("FAST_MODE", "0") == "1" or os.getenv("CI") == "true"
    SYMBOLS = ["NIFTY", "SENSEX"]

    n_candidates = 10 if FAST_MODE else 50
    n_folds = 2 if FAST_MODE else 3

    loader = DataLoader()
    market = MarketHoursAdapter()
    store = ChampionStore()
    publisher = SignalPublisher()

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"packages/strategy_foundry/results/runs/{run_ts}")
    run_dir.mkdir(parents=True, exist_ok=True)

    for symbol in SYMBOLS:
        logger.info(f"Processing {symbol}")

        # 2. Load Data (force download if needed handled by loader)
        try:
            df = loader.load_data(symbol)
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}", error=str(e))
            continue

        # 3. Generate Candidates
        gen = StrategyGenerator()
        candidates = gen.generate_batch(n_candidates)

        # 4. Backtest & Evaluate
        cost_model = CostModel(RiskConfig())
        engine = BacktestEngine(cost_model)
        evaluator = WalkForwardEvaluator(engine, n_folds=n_folds)

        passed_candidates = []

        for strat in candidates:
            # Evaluate
            res = evaluator.evaluate(strat, df)

            # Sanity Check
            min_pos_folds = 1 if FAST_MODE else 2
            min_trades = 10 if FAST_MODE else 30

            if check_sanity(res, min_trades=min_trades, min_positive_folds=min_pos_folds):
                passed_candidates.append({
                    "strategy": strat,
                    "result": res
                })

        # 5. Rank
        ranker = Ranker()
        ranking_df = ranker.rank(passed_candidates)

        if not ranking_df.empty:
            ranking_df.drop(columns=["strategy_obj"], inplace=True)
            ranking_df.to_csv(run_dir / f"ranking_{symbol}.csv", index=False)

            # 6. Champion Selection
            top_id = ranking_df.iloc[0]["id"]
            challenger = next(c for c in passed_candidates if c["strategy"].id == top_id)

            # Compare with Incumbent
            incumbent_data = store.load_current_champion(symbol)
            promoter = Promoter()

            promote = False
            if incumbent_data:
                incumbent_score = incumbent_data["score"]
                incumbent_metrics = incumbent_data["metrics"]
                if not FAST_MODE:
                     if promoter.should_promote(ranking_df.iloc[0]["score"], challenger["result"]["metrics"],
                                               incumbent_score, incumbent_metrics):
                         promote = True
            else:
                promote = True

            if promote and not FAST_MODE:
                store.save_champion(symbol, challenger["strategy"].to_dict(),
                                    float(ranking_df.iloc[0]["score"]),
                                    challenger["result"]["metrics"])
                logger.info("New Champion Promoted!", symbol=symbol, id=top_id)

        # 7. Live Signal Logic
        champ_data = store.load_current_champion(symbol)
        if not champ_data:
            publisher.publish(symbol, 0, None, status="SKIPPED", reason="No Champion")
            continue

        champ_strat = reconstruct_strategy(champ_data["strategy"])

        is_open = market.is_market_open()

        # Live Eligibility Gates
        metrics = champ_data["metrics"]
        eligible = metrics["sharpe"] >= 1.0 and metrics["max_drawdown"] <= 0.25

        if is_open and eligible:
            # We want the signal for TODAY (to position for tomorrow) OR signal from YESTERDAY (to position for today)?
            # The strategy logic is: Calculate on History, Position for NEXT OPEN.
            # If we run this during trading hours of Day T, we have history up to T-1 (Yesterday).
            # The DF might contain T (Today) as incomplete bar if loaded from live source,
            # BUT our loader (Yahoo) might return Yesterday as last row OR Today as incomplete.
            # We need to check the timestamp of the last row.

            last_dt = df.index[-1]
            now_dt = pd.Timestamp.now(tz=market.get_timezone())

            # If last row is today, it's incomplete. We should not use it for "completed bar" signal logic
            # unless the strategy is intended to run on partial bars (risky, repainting).
            # Usually daily strategies run on closed bars.
            # So we take signal generated up to T-1.
            # That signal determines position for T.
            # So if we are in T, we want the signal from T-1.

            # However, if DF has T (incomplete), `generate_positions` will output a signal for T based on T-1..T data.
            # We want the signal at index T-1 (which used data up to T-1).
            # Wait, `generate_positions` returns `combined_signal` series.
            # `combined_signal[i]` is based on indicators at `i`.
            # And `BacktestEngine` executes at `Next Open` (i+1).
            # So Signal[i] -> Position[i+1].
            # If we are at Day T, we want Position[T].
            # Position[T] is determined by Signal[T-1].

            # So we need Signal from the last COMPLETED bar.

            target_date = now_dt.date()
            last_bar_date = last_dt.date()

            use_idx = -1
            if last_bar_date == target_date:
                # Last bar is today (incomplete).
                # Signal[T] (today) is forming.
                # Signal[T-1] (yesterday) is fixed.
                # We want Position[T]. Position[T] comes from Signal[T-1].
                # So we look at `iloc[-2]`.
                # BUT, wait. `generate_positions` returns the signal calculated AT `date`.
                # If we want to trade TODAY, we need the signal generated YESTERDAY.
                use_idx = -2
            else:
                # Last bar is yesterday (or older).
                # We want Position[T] (Today).
                # Signal[T-1] (Yesterday) is at `iloc[-1]`.
                use_idx = -1

            positions = champ_strat.generate_positions(df)

            if abs(use_idx) <= len(positions):
                last_signal = positions.iloc[use_idx]
                publisher.publish(symbol, int(last_signal), champ_strat, status="OK")
            else:
                publisher.publish(symbol, 0, champ_strat, status="SKIPPED", reason="Insufficient Data")

        else:
            reason = "Market Closed" if not is_open else "Champion Not Eligible"
            publisher.publish(symbol, 0, champ_strat, status="SKIPPED", reason=reason)

    logger.info("Run completed", dir=str(run_dir))

if __name__ == "__main__":
    main()
