"""Simple Cost Model"""

class CostModel:
    def __init__(self, slippage_bps: float = 5.0, brokerage: float = 20.0, tax_bps: float = 3.0):
        self.slippage_pct = slippage_bps / 10000.0
        self.brokerage = brokerage
        self.tax_pct = tax_bps / 10000.0

    def apply(self, price: float, quantity: int, side: int) -> float:
        """
        Returns net price after costs.
        Side: 1 for Buy, -1 for Sell
        """
        # Slippage: Buy higher, Sell lower
        exec_price = price * (1 + (side * self.slippage_pct))
        exec_val = exec_price * quantity

        # Taxes
        taxes = exec_val * self.tax_pct

        # Total Cost
        total_cost = taxes + self.brokerage

        # If Buy: You pay execution value + costs
        # If Sell: You receive execution value - costs

        if side == 1:
            return - (exec_val + total_cost)
        else:
            return exec_val - total_cost

    def estimate_bps_drag(self) -> float:
        """Rough estimate of round-trip drag in bps"""
        return (self.slippage_pct * 2 + self.tax_pct * 2) * 10000 + 2 # +2 for brokerage buffer
