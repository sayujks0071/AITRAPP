from datetime import datetime, time
import pytz

IST = pytz.timezone('Asia/Kolkata')

def is_market_open() -> bool:
    """
    Check if market is open (Mon-Fri, 09:15-15:30 IST).
    Simple fallback implementation.
    """
    now = datetime.now(IST)

    # Weekends
    if now.weekday() >= 5: # Sat=5, Sun=6
        return False

    current_time = now.time()
    market_open = time(9, 15)
    market_close = time(15, 30)

    return market_open <= current_time <= market_close
