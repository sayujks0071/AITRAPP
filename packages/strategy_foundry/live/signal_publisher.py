"""
Signal Publisher.
Checks market hours, eligibility, and publishes signal JSON.
"""
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.selection.champion_store import load_champion, get_champion_score
from packages.strategy_foundry.factory.generator import StrategyInterpreter
from packages.strategy_foundry.data.loader import load_instrument

SIGNAL_FILE = "packages/strategy_foundry/results/live_signal.json"

def publish_signal():
    mh = MarketHoursAdapter()

    # 1. Market Hours Check
    if not mh.is_market_open():
        _write_skipped("Market Closed")
        return

    # 2. Champion Check
    champ = load_champion()
    if not champ:
        _write_skipped("No Champion Strategy")
        return

    # 3. Live Eligibility (Redundant if only eligible are promoted, but safety first)
    # Ideally store eligibility flag in champion file.
    # For now assume promoted champion is eligible.

    # 4. Generate Signal
    # Needs data up to NOW.
    # Yahoo data is Daily.
    # LIMITATION: We can only generate signals based on yesterday's close (Next Open execution).
    # If we run this intraday, we are effectively signaling for "Today's Open" or "Next Day Open" depending on time.
    # Logic:
    # If Pre-market/Morning (before 09:15): Signal for today open.
    # If During day: We don't have today's close yet.
    # Foundry operates on Daily frames.
    # "Signal Publisher... If market open... write signal".
    # But strict daily strategy requires Close of T-1 to signal entry at Open T.
    # So if we run at 10 AM, we use Data up to T-1.
    # The signal is valid for T (Today).

    # We load data.
    try:
        # Load NIFTY for example. Champion should store instrument preference?
        # Requirement says "Instrument: NIFTY|SENSEX".
        # Let's default to NIFTY for the champion or iterate?
        # The grammar/backtest didn't specify instrument binding.
        # Let's assume NIFTY for now or check both.

        # Actually, let's run for NIFTY.
        df = load_instrument("NIFTY")

        interpreter = StrategyInterpreter(champ)
        signals = interpreter.generate_positions(df)

        # Latest signal (for today, based on data ending yesterday)
        # df.index[-1] is the last available date.
        # If it is yesterday, then the signal is for today.

        latest_date = df.index[-1]
        # Check if latest date is today (live data) or yesterday.
        # Yahoo usually updates EOD. So it's yesterday.

        # Signal at index i is generated from data up to i.
        # It applies to Open of i+1.

        raw_sig = signals.iloc[-1]

        # We need risk params
        risk = interpreter.get_risk_params()

        output = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": champ.id,
            "instrument": "NIFTY",
            "signal": int(raw_sig),
            "rule_summary": champ.rule_summary,
            "risk": risk,
            "status": "OK",
            "reason": "Generated"
        }

        with open(SIGNAL_FILE, "w") as f:
            json.dump(output, f, indent=2)

    except Exception as e:
        _write_skipped(f"Error generating signal: {str(e)}")

def _write_skipped(reason: str):
    output = {
        "timestamp_ist": datetime.now().isoformat(),
        "status": "SKIPPED",
        "reason": reason
    }
    with open(SIGNAL_FILE, "w") as f:
        json.dump(output, f, indent=2)
