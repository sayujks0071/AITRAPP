"""
Market Hours Adapter
"""
from datetime import datetime, time
import pytz

IST = pytz.timezone("Asia/Kolkata")

class MarketHours:
    @staticmethod
    def is_market_open(dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(IST)

        # Simple check: Mon-Fri, 09:15 - 15:30
        if dt.weekday() >= 5:
            return False

        current_time = dt.time()
        start = time(9, 15)
        end = time(15, 30)

        return start <= current_time <= end

    @staticmethod
    def get_flatten_time() -> time:
        return time(15, 25)

    @staticmethod
    def filter_market_hours(df, timezone="Asia/Kolkata"):
        """
        Filter DataFrame to keep only market hours (09:15 to 15:30).
        Assumes index is datetime aware or convertible.
        """
        if df.empty:
            return df

        # Ensure index is datetime
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            df.index = pd.to_datetime(df.index)

        # Convert to IST if needed
        # (Assuming data is either UTC or IST, usually backtest data is normalized)
        # For this implementation, we assume the index is already in the correct timezone or naive (and treated as IST)

        indexer = df.index.indexer_between_time("09:15", "15:30")
        return df.iloc[indexer]

    @staticmethod
    def is_trading_holiday(date):
        # TODO: Hook into packages.core.nse_holidays if available
        # For now, rely on weekend check in is_market_open
        return False
