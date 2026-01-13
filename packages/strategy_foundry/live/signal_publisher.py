import json
import os
from datetime import datetime
import pytz
from packages.strategy_foundry.live.market_hours import is_market_open
from packages.strategy_foundry.selection.champion_store import load_champion
from packages.strategy_foundry.factory.generator import GeneratedStrategy
from packages.strategy_foundry.data.loader import get_historical_data
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "../results")
LIVE_SIGNAL_FILE = os.path.join(RESULTS_DIR, "live_signal.json")

def publish_signal(instrument="NIFTY"):
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    # Check Market Hours
    if not is_market_open(now):
        _write_signal({"status": "SKIPPED", "reason": "Market Closed", "timestamp_ist": now.isoformat()})
        return

    # Load Champion
    champ = load_champion()
    if not champ:
        _write_signal({"status": "SKIPPED", "reason": "No Champion", "timestamp_ist": now.isoformat()})
        return

    # Check Eligibility (Re-check if needed, but we assume store has valid)
    # Actually we should check live eligibility flags if stored.

    # Generate Signal
    # Load data
    df = get_historical_data(instrument)

    # Create Strategy
    strat = GeneratedStrategy(champ) # Config passed

    # Generate positions
    positions = strat.generate_positions(df)

    # Latest Signal
    # Position for TODAY (based on history)
    # generate_positions returns Target Position.
    # If using Daily bars, we are generating signal for "Tomorrow Open" based on "Today Close".
    # During live market (intraday), we rely on "Yesterday Close" to determine "Today Position"?
    # OR are we using Intraday data?
    # Foundry is Daily.
    # So: At 9:15, we check Yesterday's data -> Signal for Today.
    # If today is T. We have data up to T-1.
    # We run strat on data ending T-1.
    # Signal says: Be Long/Short/Flat for T.

    last_pos = positions.iloc[-1]

    # JSON
    signal_data = {
        "timestamp_ist": now.isoformat(),
        "champion_id": champ["id"],
        "instrument": instrument,
        "signal": int(last_pos),
        "rule_summary": str(champ.get("entry", "N/A")),
        "risk": champ.get("exit", {}),
        "status": "OK",
        "reason": "Live Signal"
    }

    _write_signal(signal_data)
    logger.info("Published live signal", signal=last_pos)

def _write_signal(data):
    with open(LIVE_SIGNAL_FILE, "w") as f:
        json.dump(data, f, indent=2)
