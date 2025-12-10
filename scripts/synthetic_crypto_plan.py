#!/usr/bin/env python3
"""Synthetic crypto plan injector for paper mode testing"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.core.config import AppConfig
from packages.core.venues.crypto_router import CryptoRouter
from packages.core.models import Venue


async def main():
    """Inject a synthetic crypto trading plan"""
    # Load config
    config_path = os.getenv("CONFIG_PATH", "configs/app.yaml")
    if not Path(config_path).exists():
        print(f"❌ Config not found: {config_path}")
        print("   Run: cp configs/crypto_paper.yaml configs/app.yaml")
        sys.exit(1)
    
    app_config = AppConfig(config_path)
    
    # Check if in crypto mode
    if app_config.mode.value not in ("CRYPTO_PAPER", "CRYPTO_LIVE"):
        print(f"❌ Not in crypto mode: {app_config.mode.value}")
        print("   Set APP_MODE=CRYPTO_PAPER")
        sys.exit(1)
    
    # Get API credentials
    venue_config = getattr(app_config, "venue", {})
    secrets_env = venue_config.get("secrets_env", {})
    api_key = os.getenv(secrets_env.get("api_key", "BINANCE_API_KEY"), "")
    api_secret = os.getenv(secrets_env.get("api_secret", "BINANCE_API_SECRET"), "")
    
    if not api_key or not api_secret:
        print("⚠️  API credentials not set (using paper simulation)")
        api_key = "paper_key"
        api_secret = "paper_secret"
    
    # Initialize exchange and router
    venue_name = venue_config.get("name", "BINANCE_SPOT")
    venue = Venue[venue_name] if venue_name in [v.name for v in Venue] else Venue.BINANCE_SPOT
    
    # Choose exchange based on venue
    if venue == Venue.BINANCE_SPOT:
        from packages.exchanges.binance_spot import BinanceSpot
        use_testnet = (app_config.mode.value == "CRYPTO_PAPER") or (os.getenv("BINANCE_TESTNET") == "1")
        exchange = BinanceSpot(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
    else:
        from packages.exchanges.kraken_spot import KrakenSpot
        exchange = KrakenSpot(api_key=api_key, api_secret=api_secret, testnet=(app_config.mode.value == "CRYPTO_PAPER"))
    
    router = CryptoRouter(
        exchange=exchange,
        config=app_config,
        venue=venue,
        paper_mode=(app_config.mode.value == "CRYPTO_PAPER")
    )
    
    await router.initialize()
    
    # Minimal synthetic LONG with attached client OCO
    plan = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "qty": 0.001,
        "type": "MARKET",
        "stop_pct": 0.005,  # 0.5% stop
        "tp_pct": 0.010,    # 1.0% take-profit
        "client_plan_id": f"crypto_oco_smoke_{int(asyncio.get_event_loop().time())}"
    }
    
    print(f"📋 Injecting plan: {plan['client_plan_id']}")
    print(f"   Symbol: {plan['symbol']}")
    print(f"   Side: {plan['side']}")
    print(f"   Qty: {plan['qty']}")
    
    ok, plan_id = await router.simulate_plan(plan)
    
    if ok:
        print(f"✅ SIM_OK: {ok}, Plan ID: {plan_id}")
        return 0
    else:
        print(f"❌ SIM_FAILED: {plan_id}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

