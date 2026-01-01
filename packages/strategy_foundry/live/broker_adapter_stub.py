"""Broker Adapter Stub"""
import logging

logger = logging.getLogger(__name__)

class BrokerAdapterStub:
    """
    STUB ONLY. NO REAL ORDERS.
    This class mimics a broker interface but only logs actions.
    Real execution requires ENABLE_LIVE and proper configuration in the Core system.
    """
    def __init__(self, enable_live: bool = False):
        self.enable_live = enable_live
        if enable_live:
            logger.warning("BrokerAdapterStub initialized in LIVE mode (STUB ONLY)")

    def place_order(self, symbol: str, side: str, quantity: int):
        if self.enable_live:
            logger.info(f"[STUB-LIVE] Would place order: {side} {quantity} {symbol}")
        else:
            logger.info(f"[PAPER] Would place order: {side} {quantity} {symbol}")
