from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE
import pytz

IST = pytz.timezone("Asia/Kolkata")

def is_market_open_now():
    guard = MarketHoursGuard()
    return guard.is_market_open()
