
import pytest
from datetime import datetime, time
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

IST = pytz.timezone("Asia/Kolkata")

class TestMarketHours:
    def test_market_hours_is_expiry_day(self):
        """Test is_expiry_day logic, specifically the 'next_thursday' logic which might fail at end of month"""
        guard = MarketHoursGuard()

        # Test Case: A Thursday near the end of the month where adding 7 days pushes it to next month
        # Example: Jan 25, 2024 (Thursday) -> Jan 25 + 7 = Feb 1. So Jan 25 is last Thursday? No.
        # Jan 2024: 4, 11, 18, 25. Feb 1 is Thursday.

        # Let's verify the logic in `is_expiry_day`:
        # next_thursday = dt.replace(day=dt.day + 7)
        # This will CRASH if dt.day + 7 > days in month.

        # Example: Jan 25, 2024. dt.day = 25. 25 + 7 = 32.
        # datetime.replace(day=32) -> ValueError: day is out of range for month

        # Let's try to trigger this crash.
        dt = datetime(2024, 1, 25, 10, 0, 0) # Thursday

        try:
            guard.is_expiry_day(dt)
        except ValueError as e:
            pytest.fail(f"is_expiry_day crashed with ValueError: {e}")
        except Exception as e:
            pytest.fail(f"is_expiry_day crashed with {type(e).__name__}: {e}")
