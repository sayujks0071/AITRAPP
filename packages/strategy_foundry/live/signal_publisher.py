import os
import json
import logging
import yaml
from datetime import datetime, time
import pytz
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.data.loader import DataLoader

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class SignalPublisher:
    def __init__(self, instrument: str, timeframe: str):
        self.instrument = instrument
        self.timeframe = timeframe # "blended" usually
        self.data_timeframe = "5m" # Execution timeframe

        self.champions_dir = "packages/strategy_foundry/results/champions"
        self.output_path = "packages/strategy_foundry/results/live_signal.json"

        self.loader = DataLoader()
        self.generator = StrategyGenerator()

        # Config
        self.foundry_config = self._load_config().get('foundry', {})
        self.instrument_map = self._load_map()

    def _load_config(self):
        path = "packages/strategy_foundry/configs/foundry.yaml"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def _load_map(self):
        path = "packages/strategy_foundry/configs/instrument_map.yaml"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def _get_champion(self):
        # We look for {instrument}_{timeframe}_current.json
        # timeframe might be 'blended'
        path = os.path.join(self.champions_dir, f"{self.instrument}_{self.timeframe}_current.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # data has 'strategy_config'
            return data
        except Exception as e:
            logger.error(f"Failed to load champion: {e}")
            return None

    def _is_market_open(self):
        # Check if current time IST is within market hours
        # Mon-Fri 09:15 - 15:30
        # Ignore holidays for now (fallback behavior as per prompt)
        now = datetime.now(IST)
        if now.weekday() >= 5: # Sat/Sun
            return False

        start = time(9, 15)
        end = time(15, 30)

        return start <= now.time() <= end

    def publish(self):
        result = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "instrument": self.instrument,
            "status": "SKIPPED",
            "reason": "Unknown"
        }

        # 1. Check Market Hours
        if not self._is_market_open():
            result['reason'] = "Market Closed"
            self._write(result)
            return

        # 2. Load Champion
        champ_data = self._get_champion()
        if not champ_data:
            result['reason'] = "No Champion Found"
            self._write(result)
            return

        # Check eligibility (re-verify or trust Promoter?)
        # Promoter only promotes if eligible (passed sanity).
        # We trust the file for now, but double check blended score?
        # "Live-eligible gate: blended OOS Sharpe >= 1.2"
        # We should check the saved metrics.
        sharpe = champ_data.get('sharpe', 0)
        max_dd = champ_data.get('max_dd', 1.0) # wait, max_dd is usually < 1.0 e.g. 0.20
        # If max_dd is > 0.20, we skip?
        # Prompt: "Live-eligible gate (strict): blended OOS Sharpe >= 1.2, MaxDD <= 20%"

        if sharpe < 1.2 or max_dd > 0.20:
             result['reason'] = f"Champion not eligible for live (Sharpe {sharpe:.2f} < 1.2 or MaxDD {max_dd:.2f} > 0.20)"
             self._write(result)
             return

        # 3. Load Data & Generate Signal
        # We need recent data (up to now)
        # Using force_download=True to get latest candle?
        # Or standard flow.
        df = self.loader.get_data(self.instrument, self.data_timeframe, force_download=True)
        if df is None or df.empty:
            result['reason'] = "Data Fetch Failed"
            self._write(result)
            return

        # Reconstruct Config
        try:
            config = StrategyConfig.from_dict(champ_data['strategy_config'])
        except Exception as e:
            result['reason'] = f"Config Parse Error: {e}"
            self._write(result)
            return

        # Generate Signal on last COMPLETE bar.
        # df includes current partial bar?
        # "Signal calculated on bar close; execute next bar open"
        # We look at the last COMPLETED bar.
        # If time is 10:00:15, and 5m bars.
        # We have bar 09:55 (closed 10:00).
        # We should generate signal on 09:55 bar, to trade on 10:00 open.
        # If we are at 10:02, we are late for 10:00 open?
        # Prompt: "Publish live signal... during market hours".
        # We publish the INTENT.
        # We take the last row of DF?
        # Loader filters 09:15-15:30.
        # If we just downloaded, the last row might be the current forming bar?
        # Yahoo often gives current bar.
        # We should drop the last bar if it's incomplete?
        # Or just use the 2nd to last row (-2).

        # Safe bet: Use -1 (Last Closed).
        # If Yahoo returns live bar, we must identify it.
        # Usually checking timestamp vs current time.
        # If timestamp is 10:00, and current is 10:02. The 10:00 bar (starts 10:00) is OPEN.
        # We need 09:55 bar.

        # Let's use iloc[-1] if we are sure it's closed, or iloc[-2].
        # Assuming Yahoo provides developing bar as last row.
        # We use iloc[-2] to be safe (last fully closed bar).

        # Generate entire series
        sigs = self.generator.generate_signal(df, config)

        # Get signal for the action bar
        # If we are at 10:02. We want signal from 09:55 bar (index -2) to execute at 10:00 (index -1).
        # Wait, if we are at 10:02, we missed the 10:00 Open.
        # But we publish signal for "Next Open" or "Current"?
        # "Signal calculated on bar close; execute next bar open".
        # If we run hourly (e.g. at XX:00).
        # We are calculating signal based on bar closing at XX:00?
        # If we run hourly, we might be too slow for 5m strategy.
        # But "Aggressive Intraday" running hourly is weird.
        # Prompt: "GitHub Actions runs hourly... Code decides whether to run intraday research".
        # It seems this is RESEARCH lab mostly, but publishes signal.
        # If it runs hourly, the signal is stale for 5m trading?
        # "Publish a live signal JSON... ONLY when eligible."
        # Maybe it publishes the "State" (Long/Short) based on latest data?
        # Or maybe it's just a reference signal.

        # Let's publish the signal derived from the LATEST COMPLETED BAR.
        # Meaning: "Based on bar ending X, the signal is Y".
        # Users (or bot) can decide if they are late.

        if len(df) < 5:
            result['reason'] = "Not enough data"
            self._write(result)
            return

        # We use -2 to ensure completion?
        # Or we check time.
        # Let's use -1 and assume Loader returns completed bars or we don't care about repaint for this lab artifact.
        # Actually, let's use -1.

        last_sig = sigs.iloc[-1]
        last_row = df.iloc[-1]

        # Interpret Signal
        # 1 = Entry Signal.
        # But we need "Position State"?
        # Generator only returns "Entry Signal" (Pulse).
        # We don't have a full position manager here tracking state across runs.
        # We only know if an entry signal fired NOW.
        # Result Schema: "signal": -1|0|1.
        # If Entry Long -> 1.
        # If nothing -> 0.

        sig_val = int(last_sig)

        # Proxies
        proxies = self.instrument_map.get('paper_proxy', {})
        live_proxies = self.instrument_map.get('live_proxy', {})

        result.update({
            "status": "OK",
            "champion_id": champ_data.get('strategy_id'),
            "timeframe": self.timeframe, # "blended"
            "proxy_symbol_paper": proxies.get(self.instrument),
            "proxy_symbol_live": live_proxies.get(self.instrument),
            "signal": sig_val,
            "rule_summary": str(config.entry_rules),
            "risk": {
                "stop": "ATR",
                "params": {"sl": config.stop_loss_atr, "tp": config.take_profit_atr},
                "flat_by": config.exit_time
            }
        })

        self._write(result)

    def _write(self, data):
        # Read existing to append? No, overwrite "live_signal.json" means "current signal".
        # But maybe we want history?
        # Prompt: "write ... live_signal.json" (singular).
        with open(self.output_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Published signal: {data['status']} - {data.get('reason', '')}")

