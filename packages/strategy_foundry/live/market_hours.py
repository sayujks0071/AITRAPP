"""Live Market Check"""
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

def is_market_open_for_signal() -> bool:
    mh = MarketHoursAdapter()
    return mh.is_market_open()
