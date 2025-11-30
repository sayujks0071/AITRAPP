"""Real-time PnL guardrail (RMS) that triggers kill switch on loss breach."""
import asyncio
from typing import Awaitable, Callable, Optional

import structlog

from packages.core.notification import NotificationService

logger = structlog.get_logger(__name__)


class RMSMonitor:
    """Polls broker positions, aggregates MTM, and enforces daily loss/profit limits."""

    def __init__(
        self,
        kite_client,
        kill_switch: Callable[[str], Awaitable[None]],
        notifier: Optional[NotificationService],
        *,
        max_daily_loss: float,
        max_daily_profit: Optional[float],
        poll_interval: int = 15,
        app_state: Optional[object] = None,
    ) -> None:
        # Loss limit should always be negative for clarity
        self.max_daily_loss = -abs(max_daily_loss)
        self.max_daily_profit = max_daily_profit
        self.poll_interval = max(5, int(poll_interval))
        self.kite = kite_client
        self.kill_switch = kill_switch
        self.notifier = notifier
        self.app_state = app_state
        self._stop: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None
        self._profit_alerted = False
        self._breach_triggered = False

    def start(self, stop_event: asyncio.Event) -> asyncio.Task:
        """Start monitoring; returns the running task."""
        self._stop = stop_event
        self._task = asyncio.create_task(self._run(), name="rms-monitor")
        logger.info(
            "RMS monitor started",
            max_daily_loss=self.max_daily_loss,
            max_daily_profit=self.max_daily_profit,
            poll_interval=self.poll_interval,
        )
        return self._task

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        while not (self._stop and self._stop.is_set()):
            try:
                positions = await loop.run_in_executor(None, self.kite.positions)
                net_positions = positions.get("net") if isinstance(positions, dict) else None
                total_pnl = sum(
                    float(p.get("m2m") or 0.0) for p in net_positions
                ) if net_positions else 0.0

                if self.app_state is not None:
                    setattr(self.app_state, "rms_pnl", total_pnl)

                # Loss breach -> immediate kill switch
                if total_pnl <= self.max_daily_loss and not self._breach_triggered:
                    self._breach_triggered = True
                    msg = (
                        f"🚨 RMS breach: P&L {total_pnl:.2f} <= limit {self.max_daily_loss:.2f}. "
                        "Triggering kill switch."
                    )
                    logger.critical(msg)
                    if self.notifier and self.notifier.is_configured():
                        self.notifier.send(msg, level="CRITICAL")
                    await self.kill_switch("RMS_BREACH")
                    break

                # Profit target hit -> alert once (non-fatal)
                if (
                    self.max_daily_profit is not None
                    and total_pnl >= self.max_daily_profit
                    and not self._profit_alerted
                ):
                    self._profit_alerted = True
                    msg = (
                        f"💰 RMS target: P&L {total_pnl:.2f} "
                        f">= profit target {self.max_daily_profit:.2f}"
                    )
                    logger.info(msg)
                    if self.notifier and self.notifier.is_configured():
                        self.notifier.send(msg, level="INFO")

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("RMS monitor error", error=str(e))

            await asyncio.sleep(self.poll_interval)

        logger.info("RMS monitor stopped")

    async def stop(self) -> None:
        """Request stop and await task completion."""
        if self._stop:
            self._stop.set()
        if self._task:
            try:
                await self._task
            except Exception:
                logger.warning("Error stopping RMS monitor", exc_info=True)
