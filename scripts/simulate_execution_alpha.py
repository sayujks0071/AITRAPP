#!/usr/bin/env python3
"""
Simulates Execution Alpha with the LimitChaseExecutor using a mocked exchange.

Run with:
    python3 scripts/simulate_execution_alpha.py
"""
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.core.execution.limit_chaser import LimitChaseExecutor, LimitChaseConfig

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("sim")


@dataclass
class MarketTick:
    time_sec: float
    best_bid: float
    best_ask: float
    ltp: float


TICK_SEQUENCE: List[MarketTick] = [
    MarketTick(0.0, 100.0, 105.0, 102.0),
    MarketTick(1.0, 100.0, 105.0, 102.0),
    MarketTick(2.0, 101.0, 106.0, 103.0),
    MarketTick(3.0, 101.5, 106.0, 103.0),
    MarketTick(4.0, 102.0, 105.0, 103.0),
    MarketTick(5.0, 102.0, 105.0, 103.0),
    MarketTick(6.0, 104.0, 104.0, 104.0),
]


class MockKite:
    """Minimal mock of kite client wired to the provided tick sequence."""

    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.start_time = self.loop.time()
        self._orders = {}
        self.order_counter = 1000

    def _get_current_tick(self) -> MarketTick:
        elapsed = self.loop.time() - self.start_time
        valid_ticks = [t for t in TICK_SEQUENCE if t.time_sec <= elapsed]
        return valid_ticks[-1] if valid_ticks else TICK_SEQUENCE[0]

    def _maybe_fill(self, order_id: str):
        order = self._orders.get(order_id)
        if not order or order["status"] != "OPEN":
            return

        tick = self._get_current_tick()
        limit_price = order["price"]
        best_ask = tick.best_ask
        best_bid = tick.best_bid

        fill_price = limit_price
        should_fill = False

        if order["type"] == "LIMIT":
            if limit_price is None:
                should_fill = True
            elif order.get("side") == "BUY" and limit_price >= best_ask:
                should_fill = True
                fill_price = best_ask
            elif order.get("side") == "SELL" and limit_price <= best_bid:
                should_fill = True
                fill_price = best_bid

        if should_fill:
            order.update(
                {
                    "status": "COMPLETE",
                    "average_price": fill_price,
                    "filled_quantity": order.get("filled_quantity") or 100,
                }
            )
            print(
                f"   [MockExchange] ✨ LIMIT FILL {order_id} "
                f"@ {fill_price} (Bid/Ask: {best_bid}/{best_ask})"
            )

    async def quote(self, symbol: str):
        tick = self._get_current_tick()
        return {
            "last_price": tick.ltp,
            "depth": {
                "buy": [{"price": tick.best_bid, "quantity": 500}],
                "sell": [{"price": tick.best_ask, "quantity": 500}],
            },
        }

    async def place_order(self, *, price, order_type, quantity, side, **kwargs):
        order_id = str(self.order_counter)
        self.order_counter += 1
        self._orders[order_id] = {
            "status": "OPEN",
            "price": price,
            "type": order_type,
            "filled_quantity": 0,
            "average_price": 0.0,
            "side": side,
        }
        print(f"   [MockExchange] New Order {order_id}: {order_type} {side} @ {price}")

        if order_type == "MARKET":
            tick = self._get_current_tick()
            fill_price = tick.best_ask if side == "BUY" else tick.best_bid
            self._orders[order_id].update(
                {
                    "status": "COMPLETE",
                    "average_price": fill_price,
                    "filled_quantity": quantity,
                }
            )
            print(f"   [MockExchange] MARKET FILL {order_id} @ {fill_price}")
        return order_id

    async def modify_order(self, order_id, price, **kwargs):
        if order_id in self._orders:
            self._orders[order_id]["price"] = price
            print(f"   [MockExchange] Modify {order_id} -> {price}")
        return True

    async def cancel_order(self, order_id, **kwargs):
        if order_id in self._orders:
            self._orders[order_id]["status"] = "CANCELLED"
            print(f"   [MockExchange] Cancel {order_id}")
        return True

    def orders(self):
        snapshot = []
        for oid in list(self._orders.keys()):
            self._maybe_fill(oid)
            entry = {"order_id": oid, **self._orders[oid]}
            snapshot.append(entry)
        return snapshot

    async def order_history(self, order_id):
        order = self._orders.get(order_id)
        if not order:
            return []

        self._maybe_fill(order_id)
        return [self._orders[order_id]]


async def run_simulation():
    print("🏎️  STARTING EXECUTION ALPHA SIMULATION (BUY SIDE)")
    print("-" * 60)
    print("SCENARIO: Option spread starts at 100/105. BUY wants best fill.")
    print("          Market orders pay 105.00 immediately.")
    print("          Limit Chase tries to capture spread.")
    print("-" * 60)

    mock_kite = MockKite()

    config = LimitChaseConfig(
        tick_size=0.05,
        step_seconds=1.0,
        max_slippage_abs=10.0,
        verbose_logging=True,
    )
    chaser = LimitChaseExecutor(mock_kite, config)

    execute_fn = getattr(chaser, "execute", None)
    execute_kwargs = {
        "symbol": "NIFTY24NOV24000CE",
        "side": "BUY",
        "quantity": 100,
        "product": "NRML",
        "variety": "regular",
        "tag": "SIM_TEST",
        "meta": {"scenario": "volatile_option"},
    }
    if execute_fn is None:
        execute_fn = chaser.execute_limit_chase

    result = await execute_fn(**execute_kwargs)
    avg_price = getattr(result, "avg_price", None)
    if avg_price is None:
        avg_price = getattr(result, "avg_fill_price", 0.0) or 0.0

    print("-" * 60)
    print(f"RESULT: {result.status}")
    print(f"Filled Qty: {result.filled_qty}")
    print(f"Filled Price: {avg_price:.2f}")

    market_price = TICK_SEQUENCE[0].best_ask
    savings = (market_price - avg_price) * execute_kwargs["quantity"]

    print(f"Market Order Cost: {market_price:.2f}")
    print(f"Alpha Generated:   {market_price - avg_price:.2f} pts per lot")
    print(f"Total Savings:     ₹{savings:.2f}")

    if avg_price < market_price:
        print("✅ SUCCESS: Limit Chase beat the Market Order.")
    else:
        print("❌ FAILURE: No alpha generated.")


if __name__ == "__main__":
    asyncio.run(run_simulation())
