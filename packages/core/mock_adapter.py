"""Mock Kite adapter for paper/shadow testing without hitting broker APIs."""
import asyncio
import itertools
from typing import Dict, List, Optional
import time


class MockKite:
    """
    Minimal mock of KiteConnect interface:
      - place_order, modify_order, cancel_order
      - orders, positions, ltp
    Immediate fills at the provided price (or default LTP).
    """
    def __init__(self, default_ltp: float = 100.0):
        self._order_id_seq = itertools.count(1)
        self._orders: Dict[str, dict] = {}
        self._positions: Dict[str, dict] = {}
        self._ltp_value = default_ltp
    
    def set_ltp(self, price: float) -> None:
        self._ltp_value = price
    
    async def place_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "LIMIT",
        price: Optional[float] = None,
        product: str = "NRML",
        variety: str = "regular",
        tag: Optional[str] = None,
        meta: Optional[dict] = None,
        **kwargs
    ) -> str:
        oid = f"MOCK_{next(self._order_id_seq)}"
        fill_price = price if price is not None else self._ltp_value
        now = time.time()
        order = {
            "order_id": oid,
            "tradingsymbol": symbol,
            "symbol": symbol,
            "transaction_type": side,
            "quantity": quantity,
            "filled_quantity": quantity,
            "average_price": fill_price,
            "price": price,
            "status": "COMPLETE",
            "variety": variety,
            "product": product,
            "order_type": order_type,
            "tag": tag,
            "created_at": now,
            "updated_at": now,
        }
        self._orders[oid] = order
        # Update positions (very naive)
        pos = self._positions.get(symbol, {"symbol": symbol, "quantity": 0, "avg_price": 0.0})
        qty = pos["quantity"]
        if side.upper() == "BUY":
            new_qty = qty + quantity
        else:
            new_qty = qty - quantity
        pos["quantity"] = new_qty
        pos["avg_price"] = fill_price
        self._positions[symbol] = pos
        return oid
    
    async def modify_order(self, order_id: str, price: Optional[float] = None, **kwargs) -> None:
        order = self._orders.get(order_id)
        if order and price is not None:
            order["price"] = price
            order["average_price"] = price
            order["updated_at"] = time.time()
    
    async def cancel_order(self, variety: str = "regular", order_id: str = "", **kwargs) -> None:
        if order_id in self._orders:
            self._orders[order_id]["status"] = "CANCELLED"
            self._orders[order_id]["updated_at"] = time.time()
    
    async def orders(self) -> List[dict]:
        return list(self._orders.values())
    
    async def positions(self) -> List[dict]:
        # Return positions in broker-like shape
        return [{"tradingsymbol": p["symbol"], "quantity": p["quantity"], "average_price": p["avg_price"]} for p in self._positions.values()]
    
    def ltp(self, instruments: List[str]) -> dict:
        # Return a dict similar to kite.ltp response
        out = {}
        for inst in instruments:
            out[inst] = {"last_price": self._ltp_value}
        return out
