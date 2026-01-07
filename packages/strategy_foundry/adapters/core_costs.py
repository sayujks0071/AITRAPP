from typing import Dict
try:
    from packages.core.risk import RiskManager, RiskConfig
    from packages.core.models import Instrument, InstrumentType
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

class CostAdapter:
    def __init__(self):
        if CORE_AVAILABLE:
            # Create a dummy config for fee calculation
            self.risk_manager = RiskManager(RiskConfig(
                max_capital=100000,
                per_trade_risk_pct=1.0,
                daily_loss_stop_pct=2.0,
                max_portfolio_heat_pct=10.0
            ))
        else:
            self.risk_manager = None

    def estimate_fees(self, instrument_type: str, quantity: int, entry_price: float, exit_price: float) -> float:
        """
        Estimate fees for a round trip trade.
        instrument_type: 'EQUITY', 'FUTURE', 'OPTION'
        """
        if self.risk_manager and CORE_AVAILABLE:
            # Create dummy instrument
            inst = Instrument(
                instrument_token=0,
                exchange_token=0,
                tradingsymbol="DUMMY",
                name="DUMMY",
                last_price=0,
                expiry=None,
                strike=0,
                tick_size=0.05,
                lot_size=1,
                instrument_type=InstrumentType.EQ if instrument_type == 'EQUITY' else InstrumentType.FUT,
                segment="NSE",
                exchange="NSE"
            )
            return self.risk_manager.estimate_fees(inst, quantity, entry_price, exit_price)

        # Fallback simple calculation (Zerodha-ish)
        turnover = quantity * (entry_price + exit_price)
        brokerage = min(20, 0.0003 * turnover) * 2 # 0.03% or 20 rs per side
        stt = 0.00025 * (quantity * exit_price) # 0.025% on sell (intraday eq)
        txn = 0.0000325 * turnover
        gst = (brokerage + txn) * 0.18
        sebi = (turnover / 10000000) * 10
        stamp = (quantity * entry_price) * 0.00003

        return brokerage + stt + txn + gst + sebi + stamp
