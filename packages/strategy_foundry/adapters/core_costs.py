from dataclasses import dataclass

@dataclass
class TransactionCosts:
    slippage_bps: float = 5.0
    all_in_cost_bps: float = 3.0 # Brokerage + STT + Exchange + GST approx for index

    def calculate_cost(self, price: float, quantity: float, side: str) -> float:
        # Cost = Value * (Slippage + Fees)
        value = price * quantity
        total_bps = self.slippage_bps + self.all_in_cost_bps
        return value * (total_bps / 10000.0)
