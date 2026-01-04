import json
from datetime import datetime
import pytz
from pathlib import Path
from typing import Dict, Any
import structlog

from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.selection.promote import load_current_champion
from packages.strategy_foundry.adapters.core_market_hours import is_market_open

logger = structlog.get_logger(__name__)

RESULTS_DIR = Path("packages/strategy_foundry/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def publish_live_signal(symbol: str, df: Any):
    """
    Generate and publish live signal JSON if market is open and champion exists.
    """
    champion_data = load_current_champion(symbol)

    if not champion_data:
        _write_signal(symbol, "SKIPPED", "No champion found")
        return

    # Reconstruct Strategy
    strategy = Strategy(champion_data["config"])

    # Check Market Hours
    if not is_market_open():
        _write_signal(symbol, "SKIPPED", "Market is closed")
        return

    # Check Eligibility
    # OOS Sharpe >= 1.0, MaxDD <= 25%, etc. (Should be checked during promotion/ranking)
    # But double check here if needed.

    # Generate Signal
    # We need to run generation on the latest DF.
    # The DF passed here should be up to date (loaded in run_hourly).

    if df.empty:
        _write_signal(symbol, "SKIPPED", "No data available")
        return

    positions = strategy.generate_positions(df)
    current_signal = int(positions.iloc[-1])

    # Construct Payload
    payload = {
        "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "champion_id": champion_data["id"],
        "instrument": symbol,
        "signal": current_signal,
        "rule_summary": strategy.rule_summary(),
        "risk": _extract_risk_params(strategy),
        "status": "OK"
    }

    _write_signal(symbol, "OK", None, payload)

def _extract_risk_params(strategy: Strategy) -> Dict[str, Any]:
    risk = {}
    for block in strategy.blocks:
        if block["category"] == "risk":
            risk[block["type"]] = block["params"]
    return risk

def _write_signal(symbol: str, status: str, reason: str = None, payload: Dict = None):
    data = payload if payload else {
        "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "instrument": symbol,
        "status": status,
        "reason": reason
    }

    # We maintain one file per instrument or one global?
    # User said: `packages/strategy_foundry/results/live_signal.json`
    # Implies a single file. If we run for NIFTY and SENSEX, we might overwrite.
    # Let's write specific files or merge.
    # User requirement: "packages/strategy_foundry/results/live_signal.json"

    # If we run sequentially, we might want a dict with keys for instruments.
    # Or just one main signal file.
    # Let's use `live_signal_{symbol}.json` to be safe, or just overwrite if only one "Active" target.
    # User prompt implies "live_signal.json". Let's try to update it or write it.

    file_path = RESULTS_DIR / "live_signal.json"

    # If exists, read and update
    full_content = {}
    if file_path.exists():
        try:
            with open(file_path, "r") as f:
                full_content = json.load(f)
        except:
            pass

    full_content[symbol] = data

    with open(file_path, "w") as f:
        json.dump(full_content, f, indent=2)

    logger.info("Published signal", symbol=symbol, status=status)
