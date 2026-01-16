from typing import Dict

class CostModel:
    def __init__(self, slippage_bps_per_side: float, brokerage_per_order: float, spread_guard_bps: float, tax_bps: float):
        self.slippage_bps = slippage_bps_per_side
        self.brokerage = brokerage_per_order
        self.spread_guard_bps = spread_guard_bps
        self.tax_bps = tax_bps

    def get_slippage_price(self, price: float, direction: int) -> float:
        """
        Returns price after slippage.
        Direction: 1 (Buy), -1 (Sell)
        """
        # Buy: Price * (1 + slippage)
        # Sell: Price * (1 - slippage)
        slip = self.slippage_bps / 10000.0
        if direction == 1:
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    def calculate_cost(self, price: float, quantity: int, side: str) -> float:
        """
        Returns absolute cost in currency.
        Side: 'BUY' or 'SELL'
        """
        # Tax + Brokerage
        # Tax is usually % of turnover.
        # Brokerage is flat.
        turnover = price * quantity
        tax = turnover * (self.tax_bps / 10000.0)
        return tax + self.brokerage
