import pytest
from datetime import datetime, timedelta
import pytz
from packages.core.market_hours import MarketHoursGuard

def test_is_expiry_day_safe_logic():
    """
    Test that is_expiry_day correctly handles month boundaries and identifies expiry days.
    """
    guard = MarketHoursGuard()

    # Jan 25, 2024 is a Thursday.
    # It is the last Thursday of Jan 2024.
    dt = datetime(2024, 1, 25, 10, 0, tzinfo=pytz.timezone("Asia/Kolkata"))

    # Should return True (it is an expiry day)
    assert guard.is_expiry_day(dt) is True

    # Jan 18, 2024 is a Thursday, but not the last one.
    dt_weekly = datetime(2024, 1, 18, 10, 0, tzinfo=pytz.timezone("Asia/Kolkata"))
    assert guard.is_expiry_day(dt_weekly) is True

    # Jan 24, 2024 is a Wednesday.
    dt_not_expiry = datetime(2024, 1, 24, 10, 0, tzinfo=pytz.timezone("Asia/Kolkata"))
    assert guard.is_expiry_day(dt_not_expiry) is False

    # Feb 29, 2024 is a Thursday (Leap Year) and last day of month
    dt_leap = datetime(2024, 2, 29, 10, 0, tzinfo=pytz.timezone("Asia/Kolkata"))
    assert guard.is_expiry_day(dt_leap) is True
