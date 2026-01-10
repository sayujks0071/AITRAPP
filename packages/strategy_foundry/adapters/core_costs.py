"""
Adapter for costs.
"""
from packages.core.config import RiskConfig

# Default foundry risk config
# Pass as dictionary to match core.config.RiskConfig definition
DEFAULT_RISK_CONFIG = RiskConfig({
    "per_trade_risk_pct": 1.0,
    "daily_loss_stop_pct": 2.0,
    "max_portfolio_heat_pct": 5.0,
    "max_position_size_multiplier": 1.0,
    "fees_per_order": 20.0
})

# We will just define a cost model class for backtesting
class CostModel:
    def __init__(self, slippage_bps: float = 5.0, brokerage_per_order: float = 20.0):
        self.slippage_bps = slippage_bps
        self.brokerage_per_order = brokerage_per_order

    def estimate_cost(self, price: float, quantity: int, side: str) -> float:
        """
        Estimate cost for ONE SIDE of a trade (entry or exit).
        Includes slippage + brokerage + approx taxes.
        """
        value = price * quantity

        # Slippage
        slippage = value * (self.slippage_bps / 10000.0)

        # Brokerage
        # Flat 20 or 0.03%
        brokerage = min(self.brokerage_per_order, value * 0.0003)

        # Approx Taxes (STT + Exchange + GST + Stamp) ~ 0.03% total roughly for intraday equity/futures mix
        # STT is 0 on buy (intraday equity), 0.025% on sell
        # Let's use a conservative flat rate of 3bps for taxes
        taxes = value * 0.0003

        return slippage + brokerage + taxes
