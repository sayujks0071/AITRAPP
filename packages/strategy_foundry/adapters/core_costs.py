from typing import Optional

class FoundryCosts:
    """
    Cost estimation adapter.
    Defaults to simple bps model if core not available or for backtesting simplicity.
    """

    def __init__(self, slippage_bps: float = 5.0, brokerage_per_order: float = 20.0, taxes_bps: float = 3.0):
        self.slippage_bps = slippage_bps
        self.brokerage = brokerage_per_order
        self.taxes_bps = taxes_bps

    def estimate_transaction_cost(self, price: float, quantity: int, side: str = "BUY") -> float:
        """
        Estimate total cost for one leg (entry or exit).
        Returns absolute cost value in currency.
        """
        value = price * quantity

        # Slippage cost
        slippage_cost = value * (self.slippage_bps / 10000.0)

        # Brokerage (Flat fee usually)
        brokerage_cost = self.brokerage

        # Taxes (STT, etc approximated as bps of turnover)
        tax_cost = value * (self.taxes_bps / 10000.0)

        return slippage_cost + brokerage_cost + tax_cost

    def get_slippage_price(self, price: float, side: str) -> float:
        """
        Return the execution price after slippage.
        """
        if side.upper() == "BUY":
            return price * (1 + self.slippage_bps / 10000.0)
        else:
            return price * (1 - self.slippage_bps / 10000.0)
