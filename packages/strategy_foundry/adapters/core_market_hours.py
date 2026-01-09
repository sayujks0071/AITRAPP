"""
Core Market Hours Adapter
Handling market hours and holidays.
"""
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

class MarketHoursGuard:
    @staticmethod
    def is_market_open(timestamp: datetime = None) -> bool:
        if timestamp is None:
            timestamp = datetime.now(IST)
        else:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=IST)
            else:
                timestamp = timestamp.astimezone(IST)

        # Check Weekend
        if timestamp.weekday() >= 5: # Sat=5, Sun=6
            return False

        # Check Time (09:15 - 15:30)
        start_time = timestamp.replace(hour=9, minute=15, second=0, microsecond=0)
        end_time = timestamp.replace(hour=15, minute=30, second=0, microsecond=0)

        if start_time <= timestamp <= end_time:
            return True

        return False
