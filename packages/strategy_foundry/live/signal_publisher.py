"""Live Signal Publisher"""
import json
import datetime
import structlog
from pathlib import Path
from ..adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

RESULTS_DIR = Path(__file__).parent.parent / "results"
LIVE_SIGNAL_FILE = RESULTS_DIR / "live_signal.json"

def publish_signal(champion: dict, signal_val: int, instrument: str, reason: str):
    """Publish the live signal JSON"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    mh = MarketHoursAdapter()
    is_open = mh.is_market_open()

    # Gate: Must be market open AND eligible
    status = "OK"

    # If reason contains "Ineligible", we mark as skipped
    if "Ineligible" in reason:
        status = "SKIPPED"
        # reason is already set
    elif not is_open:
        status = "SKIPPED"
        reason = f"Market Closed. {reason}"

    payload = {
        "timestamp_ist": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(),
        "champion_id": champion.get("strategy", {}).get("id"),
        "instrument": instrument,
        "signal": signal_val, # -1, 0, 1
        "rule_summary": reason,
        "risk": champion.get("strategy", {}).get("risk", []),
        "status": status,
        "reason": reason
    }

    with open(LIVE_SIGNAL_FILE, "w") as f:
        json.dump(payload, f, indent=2)

    logger.info("Published live signal", file=str(LIVE_SIGNAL_FILE), status=status)
