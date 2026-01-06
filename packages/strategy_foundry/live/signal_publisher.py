import json
from pathlib import Path
from datetime import datetime
import pytz
from typing import Dict, Any
from ..factory.grammar import StrategyCandidate
from ..data.loader import load_data
from ..adapters.core_indicators import compute_all_indicators

RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def publish_signal(champion_data: Dict[str, Any], instrument: str = "NIFTY"):
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).isoformat()

    cand = StrategyCandidate.from_json(champion_data["candidate"])

    # Load latest data (ensure it includes today/latest available)
    df = load_data(instrument, days_back=300)
    if df.empty:
        _write_skipped(timestamp, "Data unavailable")
        return

    # Compute indicators
    df = compute_all_indicators(df)

    # Generate positions
    positions = cand.generate_positions(df)

    # Latest signal (Target Position)
    # We want the target position for "Now".
    # generate_positions(df) returns "positions" array where pos[i] is target state at step i.
    # Usually this means "At close of i, be in this state".
    # If market is Open, and we have live data, we check the latest bar.
    # BUT we only have Daily data.
    # If we run this intraday, the "latest" bar in Yahoo might be yesterday's close,
    # or today's incomplete candle?
    # Yahoo often updates with a lag or provides previous close.
    # If we run at 10 AM, Yahoo might show yesterday's data.
    # If we rely on Daily Strategy, we act based on Yesterday's Close (signal generated last night)
    # for Today's Open/Session.

    # So we check the last COMPLETED candle signal.
    # If today is T, we look at T-1 signal.
    # positions.iloc[-1] corresponds to the last row in DF.

    last_date = df.index[-1]

    # If last_date is Today, it's an incomplete candle? Yahoo provides incomplete daily candle sometimes.
    # For safety, let's use the signal from the last row, assuming that's the current "state".

    signal = int(positions.iloc[-1])

    # Rule Summary
    rule_summary = cand.rule_summary()

    output = {
        "timestamp_ist": timestamp,
        "champion_id": cand.id,
        "instrument": instrument,
        "signal": signal,
        "rule_summary": rule_summary,
        "risk": cand.params,
        "status": "OK",
        "last_data_date": str(last_date)
    }

    path = RESULTS_DIR / "live_signal.json"
    path.write_text(json.dumps(output, indent=2))

def _write_skipped(timestamp: str, reason: str):
    output = {
        "timestamp_ist": timestamp,
        "status": "SKIPPED",
        "reason": reason
    }
    path = RESULTS_DIR / "live_signal.json"
    path.write_text(json.dumps(output, indent=2))
