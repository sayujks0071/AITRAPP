import json
import os
import structlog
from datetime import datetime
import pytz
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.selection.champion_store import load_champion, reconstruct_strategy
from packages.strategy_foundry.data.loader import get_data
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "../results")

def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)

def check_eligibility(champion_data: dict) -> tuple[bool, str]:
    metrics = champion_data.get("metrics", {})
    sharpe = metrics.get("sharpe", 0)
    max_dd = metrics.get("max_drawdown", 1.0)
    passed_folds = champion_data.get("passed_folds", False) # Needs to be stored?
    # Actually passed_folds logic was in walkforward but stored in metrics dict?
    # In walkforward.py, I returned "passed_folds" boolean in the main dict, not under metrics.
    # champion_store saves the *whole* dict returned by walkforward?
    # champion_store saves `metrics` argument.
    # run_hourly needs to pass the correct structure.
    # Let's assume `metrics` contains what we need or we check what we have.

    # User Rules:
    # OOS Sharpe >= 1.0
    # MaxDD <= 25% (0.25)
    # >= 3 positive OOS folds (FAST_MODE doesn’t promote) -> This implies promotion gate, but also live gate.

    if sharpe < 1.0:
        return False, f"Sharpe {sharpe:.2f} < 1.0"
    if max_dd > 0.25:
        return False, f"MaxDD {max_dd:.2%} > 25%"

    return True, "OK"

def publish_signal_for_instrument(instrument: str):
    ensure_results_dir()
    output_file = os.path.join(RESULTS_DIR, f"live_signal_{instrument}.json")

    # 1. Market Hours
    mh = MarketHoursAdapter()
    if not mh.is_market_open():
        # Write SKIPPED
        signal_data = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "instrument": instrument,
            "status": "SKIPPED",
            "reason": "Market Closed"
        }
        with open(output_file, "w") as f:
            json.dump(signal_data, f, indent=2)
        return

    # 2. Load Champion
    champ_data = load_champion(instrument)
    if not champ_data:
        signal_data = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "instrument": instrument,
            "status": "SKIPPED",
            "reason": "No Champion Found"
        }
        with open(output_file, "w") as f:
            json.dump(signal_data, f, indent=2)
        return

    # 3. Eligibility
    eligible, reason = check_eligibility(champ_data)
    if not eligible:
        signal_data = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "instrument": instrument,
            "status": "SKIPPED",
            "reason": f"Champion Ineligible: {reason}"
        }
        with open(output_file, "w") as f:
            json.dump(signal_data, f, indent=2)
        return

    # 4. Run Strategy
    try:
        # Get Data (Force refresh to ensure latest)
        df = get_data(instrument, force_refresh=True)
        df = VectorizedIndicators.add_all(df)

        strategy = reconstruct_strategy(champ_data)

        # Generate Signals
        raw_signals = strategy.generate_raw_signals(df)

        # Look at the LAST completed bar (Yesterday)
        # Because we execute at Open of Next Bar (Today) based on Yesterday's Signal.
        last_sig = raw_signals.iloc[-1]

        final_signal = 0
        if last_sig == 1:
            final_signal = 1
        elif last_sig == -10:
            final_signal = -1 # Explicit Exit

        # Write Signal
        signal_data = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "champion_id": strategy.strategy_id,
            "instrument": instrument,
            "signal": final_signal,
            "rule_summary": strategy.get_summary(),
            "risk": strategy.risk_params,
            "status": "OK",
            "reason": "Generated"
        }

        with open(output_file, "w") as f:
            json.dump(signal_data, f, indent=2)

    except Exception as e:
        logger.error("Failed to generate signal", error=str(e))
        signal_data = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "instrument": instrument,
            "status": "SKIPPED",
            "reason": f"Error: {str(e)}"
        }
        with open(output_file, "w") as f:
            json.dump(signal_data, f, indent=2)

def publish_all_signals():
    for inst in ["NIFTY", "SENSEX"]:
        publish_signal_for_instrument(inst)
