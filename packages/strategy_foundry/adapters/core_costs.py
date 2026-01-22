from typing import Optional
from packages.core.risk import RiskManager
from packages.core.config import RiskConfig
from packages.core.models import Instrument, InstrumentType

class CostAdapter:
    """
    Adapter for cost estimation reusing RiskManager logic.
    """
    def __init__(self):
        # Initialize with dummy config as we only use static fee calculation logic mostly
        self.risk_manager = RiskManager(RiskConfig({}))

    def estimate_round_trip_cost(self,
                                 price: float,
                                 quantity: int,
                                 instrument_type: str = "EQUITY") -> float:
        """
        Estimate costs for entry and exit at same price (approx).
        """
        # Create a dummy instrument
        inst_type = InstrumentType.EQUITY
        if instrument_type == "FUTURES":
            inst_type = InstrumentType.FUTURES

        dummy_inst = Instrument(
            token=0,
            exchange="NSE",
            tradingsymbol="DUMMY",
            lot_size=1,
            instrument_type=inst_type,
            tick_size=0.05
        )

        # Estimate fees
        fees = self.risk_manager.estimate_fees(
            instrument=dummy_inst,
            quantity=quantity,
            entry_price=price,
            exit_price=price
        )

        return fees
