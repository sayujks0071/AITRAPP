from dataclasses import dataclass

@dataclass
class RiskConfig:
    slippage_bps: float = 5.0
    brokerage_per_order: float = 20.0
    tax_turnover_bps: float = 3.0  # Approx STT + Exch + Stamp

class CostModel:
    def __init__(self, config: RiskConfig):
        self.config = config

    def estimate_cost(self, price: float, quantity: int, side: str) -> float:
        """
        Estimate cost for a trade (one side).
        """
        turnover = price * quantity

        # Slippage
        slippage = turnover * (self.config.slippage_bps / 10000.0)

        # Brokerage
        brokerage = self.config.brokerage_per_order

        # Taxes
        taxes = turnover * (self.config.tax_turnover_bps / 10000.0)

        return slippage + brokerage + taxes
