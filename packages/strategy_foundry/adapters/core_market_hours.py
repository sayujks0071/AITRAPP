"""Adapter for core market hours logic"""
from datetime import datetime
from typing import Optional

from packages.core.market_hours import MarketHoursGuard, IST, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

# Instantiate a global guard
_guard = MarketHoursGuard()

def is_market_open(dt: Optional[datetime] = None) -> bool:
    return _guard.is_market_open(dt)

def can_place_entry(dt: Optional[datetime] = None) -> bool:
    return _guard.can_place_entry(dt)

def can_place_exit(dt: Optional[datetime] = None) -> bool:
    return _guard.can_place_exit(dt)

def get_market_hours():
    return {
        "open": MARKET_OPEN,
        "close": MARKET_CLOSE,
        "hard_close": HARD_CLOSE,
        "timezone": IST
    }
