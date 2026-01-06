"""Cost modeling adapter for strategy foundry"""
from dataclasses import dataclass

@dataclass
class CostModel:
    all_in_cost_bps_per_side: float = 3.0
    slippage_bps_per_side: float = 2.0
    spread_guard_bps: float = 1.0

    def estimate_cost(self, price: float, quantity: int, side: str = "entry") -> float:
        """Calculate total transaction cost including slippage"""
        notional = price * abs(quantity)
        total_bps = self.all_in_cost_bps_per_side + self.slippage_bps_per_side

        # Add spread guard penalty for entries in choppy markets (simplified as fixed cost here)
        # In a real dynamic model, this would check volatility
        if side == "entry":
             total_bps += self.spread_guard_bps

        return notional * (total_bps / 10000.0)

    def get_slippage_price(self, price: float, direction: int) -> float:
        """Return price adjusted for slippage
        direction: 1 for buy, -1 for sell
        """
        adjustment = price * (self.slippage_bps_per_side / 10000.0)
        return price + (adjustment * direction)
