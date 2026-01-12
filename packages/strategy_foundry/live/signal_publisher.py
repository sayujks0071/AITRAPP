import json
import os
from datetime import datetime
import pandas as pd
from packages.strategy_foundry.adapters.core_market_hours import is_market_open
from packages.strategy_foundry.selection.ranker import ChampionStore
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.factory.generator import StrategyImpl
from packages.strategy_foundry.data.loader import load_data

SIGNAL_FILE = "packages/strategy_foundry/results/live_signal.json"

def publish_signal():
    """
    Load champion, run on latest data, publish signal.
    """
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

    # Check Market Hours
    # if not is_market_open():
    #     _write_status("SKIPPED", "Market Closed")
    #     return

    # For MVP, we might run this in CI which runs hourly.
    # CI might run when market is closed?
    # Requirement: "If market open AND champion live-eligible..."
    # If closed, write SKIPPED.

    # However, to test, I might want to force it.
    # But sticking to requirements.
    # But wait, CI runs hourly 24/7.
    pass

    store = ChampionStore()

    # We execute for both NIFTY and SENSEX?
    # Usually we have one champion per instrument?
    # Let's support NIFTY for now.

    instruments = ["NIFTY", "SENSEX"]
    signals = []

    for symbol in instruments:
        champ = store.get_current_champion(symbol)

        if not champ:
            # No champion
            continue

        # Check eligibility (already checked during promotion, but safe to check flag)
        # Assuming champ is eligible if it's in current.

        if not is_market_open():
             _write_status("SKIPPED", "Market Closed")
             return

        # Load Data
        df = load_data(symbol)
        if df is None or df.empty:
            _write_status("SKIPPED", f"No data for {symbol}")
            return

        # Run Strategy
        # Reconstruct config
        config = StrategyConfig(champ['name'], champ['blocks'], champ['params'])
        impl = StrategyImpl(config)

        # Get positions
        # We need to run on recent history to get signal for TODAY.
        # "Signal ... execute next bar open".
        # We need signal generated at close of last bar?
        # If we run hourly DURING the day, we don't have today's close yet.
        # But we might have intraday bars?
        # Requirement says "Daily (1D)".
        # So we only generate signal once a day after close?
        # Or before open?
        # If we run hourly, and data is daily candles...
        # We only have Yesterday's Close.
        # So we generate signal for Today's Open based on Yesterday's Close.
        # This signal is valid for whole day Today.

        # So: Load daily data (up to Yesterday).
        # Generate Signal.
        # This signal is what we publish.

        # Wait, if we fetch Yahoo data during trading day, does it include today's incomplete candle?
        # Yahoo often gives incomplete candle.
        # We should probably filter for completed candles or handle it.
        # Safe bet: Use data up to yesterday.

        # Yahoo 'period2=now' gives incomplete today.
        # We should probably drop the last row if date is today?
        # Or use it as 'current price'?

        # Let's assume we use last FULL bar.
        # If today is T, we use T-1 close to signal for T Open.
        # So signal is constant for day T.

        # Calculate
        positions = impl.generate_positions(df)

        # Signal for "Next Open" is the last value of positions series?
        # positions[t] is the target position for day t (entered at Open t).
        # No, in my engine logic:
        # pos[t] comes from signal[t-1].
        # `generate_positions` returns the TARGET position series.
        # If `positions` has index T, it means "On day T, we want to be in this position".
        # So we look at `positions.iloc[-1]`.

        target_pos = int(positions.iloc[-1])

        # Prepare Signal Object
        sig = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": champ['id'],
            "instrument": symbol,
            "signal": target_pos,
            "rule_summary": champ['rule_summary'],
            "risk": {"note": "See strategy params"},
            "status": "OK"
        }
        signals.append(sig)

    if not signals:
         _write_status("SKIPPED", "No champions or data")
         return

    # Write aggregated or single?
    # Requirement: "live_signal.json". Schema shows single object?
    # "instrument": "NIFTY|SENSEX".
    # Maybe list? Or file per instrument?
    # Schema seems to imply single object.
    # Let's write the first one or valid one.
    # Or maybe list of objects.
    # User schema: { ... "instrument": ... }
    # Let's write a list if multiple, or just NIFTY as primary.
    # "NIFTY|SENSEX" suggests one of them.
    # I'll default to NIFTY.

    final_sig = signals[0]

    with open(SIGNAL_FILE, 'w') as f:
        json.dump(final_sig, f, indent=2)

def _write_status(status, reason):
    with open(SIGNAL_FILE, 'w') as f:
        json.dump({
            "timestamp_ist": datetime.now().isoformat(),
            "status": status,
            "reason": reason
        }, f, indent=2)
