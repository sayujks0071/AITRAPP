from typing import NamedTuple
from packages.core.config import RiskConfig
from packages.core.risk import RiskManager
from packages.core.models import Instrument, InstrumentType

# Dummy config for RiskManager initialization
DUMMY_RISK_CONFIG = RiskConfig({
    "max_capital": 100000,
    "daily_loss_stop_pct": 2.0,
    "max_portfolio_heat_pct": 10.0,
    "per_trade_risk_pct": 1.0,
    "max_position_size_multiplier": 10,
    "fees_per_order": 20.0
})

class CostEstimate(NamedTuple):
    total_fees: float
    slippage: float

class CostsAdapter:
    """
    Adapter for cost estimation.
    """

    def __init__(self):
        self.risk_manager = RiskManager(DUMMY_RISK_CONFIG)

    def estimate_costs(self, instrument_type: str, price: float, quantity: int, slippage_bps: float = 5.0) -> CostEstimate:
        """
        Estimate costs for a single leg (entry or exit).
        Note: Core `estimate_fees` calculates round-trip.
        We will approximate single leg as half of round trip + slippage.
        """

        # Create a dummy instrument for the calculator
        is_equity = instrument_type == 'EQUITY'
        is_future = instrument_type == 'FUTURE'
        is_option = instrument_type == 'OPTION'

        # Duck typing Instrument
        class MockInstrument:
            def __init__(self):
                self.is_equity = is_equity
                self.is_future = is_future
                self.is_option = is_option
                self.exchange = "NSE"
                self.tradingsymbol = "TEST"
                self.lot_size = 1 # Needed if accessed

        inst = MockInstrument()

        # RiskManager.estimate_fees calculates ROUND TRIP.
        # args: instrument, quantity, entry_price, exit_price
        round_trip_fees = self.risk_manager.estimate_fees(inst, quantity, price, price)

        single_leg_fees = round_trip_fees / 2.0

        slippage_cost = (price * quantity) * (slippage_bps / 10000.0)

        return CostEstimate(total_fees=single_leg_fees, slippage=slippage_cost)
