from datetime import datetime, time
import pytz

def is_market_open(dt: datetime = None) -> bool:
    """
    Simple fallback market hours check.
    Mon-Fri, 09:15 - 15:30 IST.
    """
    if dt is None:
        dt = datetime.now(pytz.timezone("Asia/Kolkata"))

    if dt.weekday() >= 5: # Sat, Sun
        return False

    t = dt.time()
    if t >= time(9, 15) and t <= time(15, 30):
        return True

    return False
