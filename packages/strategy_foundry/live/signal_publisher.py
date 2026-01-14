import json
import structlog
from datetime import datetime
from pathlib import Path
from packages.strategy_foundry.adapters.core_market_hours import is_market_open, IST
from packages.strategy_foundry.selection.champion_store import load_champion
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec

logger = structlog.get_logger(__name__)

SIGNAL_FILE = Path("packages/strategy_foundry/results/live_signal.json")

def _write_skipped(reason: str):
    doc = {
        "timestamp_ist": datetime.now(IST).isoformat(),
        "status": "SKIPPED",
        "reason": reason
    }
    with open(SIGNAL_FILE, "w") as f:
        json.dump(doc, f, indent=2)
    logger.info("Signal skipped", reason=reason)

def publish_signal():
    SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 1. Market Hours Check
    if not is_market_open():
        _write_skipped("Market Closed")
        return

    # 2. Load Champion
    champ_data = load_champion()
    if not champ_data:
        _write_skipped("No Champion Found")
        return

    # 3. Load Data
    spec_dict = champ_data.get("spec")
    if not spec_dict:
        _write_skipped("Invalid Champion Spec")
        return

    spec = StrategySpec.from_dict(spec_dict)

    # Use the champion's timeframe if available, else default
    timeframe = champ_data.get("timeframe", "15m")
    instrument = "NIFTY" # Default, could be in champion data too

    loader = DataLoader()
    # Fetch fresh data
    df = loader.get_data(instrument, timeframe, force_refresh=True)

    if df.empty:
        _write_skipped("No Data")
        return

    # 4. Run Backtest (Replay to get state)
    engine = BacktestEngine()
    result = engine.run(spec, df)

    state = result.get("current_state", {})
    position = state.get("position", 0)

    # 5. Construct Signal
    signal_doc = {
        "timestamp_ist": datetime.now(IST).isoformat(),
        "champion_id": champ_data.get("candidate_id"),
        "timeframe": timeframe,
        "instrument": instrument,
        "proxy_symbol_paper": loader.get_proxy_ticker(instrument),
        "proxy_symbol_live": "NIFTY 50 FUT", # Could be config driven
        "signal": position,
        "rule_summary": str(spec.entry_logic),
        "risk": {
            "stop": state.get("sl_price"),
            "target": state.get("tp_price"),
            "flat_by": spec.session_close_time
        },
        "status": "OK",
        "reason": f"Position: {position}"
    }

    with open(SIGNAL_FILE, "w") as f:
        json.dump(signal_doc, f, indent=2)

    logger.info("Signal published", signal=position, champion=champ_data.get("candidate_id"))
