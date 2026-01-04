"""
Live Signal Publisher
"""
import json
import os
import structlog
from datetime import datetime
import pytz
from packages.strategy_foundry.adapters.core_market_hours import MarketHours
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
import yaml

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class SignalPublisher:
    def __init__(self, config_path="packages/strategy_foundry/configs/foundry.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.output_file = os.path.join(self.config['system']['results_dir'], "live_signal.json")
        self.data_loader = DataLoader()

    def publish(self, champion, instrument="NIFTY"):
        """
        Generate and publish signal for the champion.
        """
        # 1. Check Market Hours
        if not MarketHours.is_market_open():
            self._write_skipped("Market Closed")
            return

        if not champion:
            self._write_skipped("No Champion Available")
            return

        # 2. Check Eligibility (Gate)
        # Assuming champion passed gates before promotion, but double check config logic if needed.
        # Here we assume the passed champion object is valid.

        # 3. Load Live Data
        # We need recent data to generate signal.
        # Strategy depends on timeframe.
        # If 5m, we need recent 5m bars.
        # IMPORTANT: Live signal generation must use the exact same data source or equivalent.
        # Foundry uses research/proxy symbols.

        tf = champion.get("timeframe", "15m")
        # Load enough data for indicators
        df = self.data_loader.get_data(instrument, tf, days=10) # 10 days enough for most indicators

        if df.empty:
            self._write_skipped("Data Unavailable")
            return

        # 4. Run Strategy on Data
        # We need to run the engine to get the signal for the *next* bar (which is now/soon).
        # The engine logic: signals calculated on bar close.
        # So we look at the last completed bar.

        engine = BacktestEngine(df, champion["strategy"])

        # Helper to get signal at last bar
        # Engine usually runs full loop. We can use internal methods.
        engine._compute_indicators(df)
        signals = engine._generate_signals(df)

        # Last bar signal
        last_sig = signals.iloc[-1] # Signal generated at close of last bar

        # Check if we should be flat (time check)
        flatten_time = MarketHours.get_flatten_time()
        now_time = datetime.now(IST).time()

        signal_val = int(last_sig)
        if now_time >= flatten_time:
            signal_val = 0 # Force flat

        # 5. Construct Payload
        payload = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "champion_id": champion["id"],
            "timeframe": tf,
            "instrument": instrument,
            "proxy_symbol_paper": self.data_loader.proxies.get(instrument, ""),
            "proxy_symbol_live": self.data_loader.instrument_map.get("live_proxy", {}).get(instrument, ""),
            "signal": signal_val,
            "rule_summary": json.dumps(champion["strategy"]), # simplified
            "risk": {
                "stop": champion["strategy"]["exit"].get("atr_stop", "N/A"),
                "flat_by": "15:25"
            },
            "status": "OK",
            "reason": ""
        }

        self._write_json(payload)
        logger.info("Published live signal", signal=signal_val)

    def _write_skipped(self, reason):
        payload = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(payload)

    def _write_json(self, payload):
        with open(self.output_file, "w") as f:
            json.dump(payload, f, indent=2)

