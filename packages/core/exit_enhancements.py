"""Enhanced exit logic with spread-specific and profit protection features"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import structlog

from packages.core.config import ExitsConfig
from packages.core.models import Position, SignalSide
from packages.core.exits import ExitManager, ExitSignal, ExitReason

logger = structlog.get_logger(__name__)


class EnhancedExitManager(ExitManager):
    """
    Enhanced exit manager with additional features:
    - Spread-specific exit logic (debit spreads, credit spreads)
    - Profit protection (lock in gains after hitting profit targets)
    - Adaptive stop loss tightening
    - Position age-based exit adjustments
    """

    def __init__(self, config: ExitsConfig):
        super().__init__(config)

        # Track profit milestones
        self.profit_milestones: Dict[str, List[float]] = {}  # position_id -> [milestone_pcts]

        # Spread-specific tracking
        self.spread_positions: Dict[str, Dict] = {}  # position_id -> spread_info

    def register_spread_position(
        self,
        position_id: str,
        spread_type: str,  # DEBIT_SPREAD, CREDIT_SPREAD, IRON_CONDOR, etc.
        net_premium: float,  # Net premium paid/received
        max_profit: float,  # Maximum possible profit
        max_loss: float,  # Maximum possible loss
    ) -> None:
        """
        Register a spread position for enhanced exit management.

        For debit spreads:
        - net_premium is negative (paid)
        - max_profit is limited by strike difference
        - max_loss is net_premium paid

        For credit spreads:
        - net_premium is positive (received)
        - max_profit is net_premium received
        - max_loss is strike difference minus premium
        """
        self.spread_positions[position_id] = {
            "spread_type": spread_type,
            "net_premium": net_premium,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "entry_time": datetime.now(),
        }

        logger.info(
            "Registered spread position",
            position_id=position_id,
            spread_type=spread_type,
            net_premium=net_premium,
            max_profit=max_profit,
            max_loss=max_loss,
        )

    def _check_spread_exits(
        self,
        position: Position,
        current_time: datetime,
    ) -> Optional[ExitSignal]:
        """
        Check spread-specific exit conditions.

        For debit spreads:
        - Exit if position reaches 70-80% of max profit
        - Exit if position loses 50% of premium paid
        - Exit if near expiry with little time value

        For credit spreads:
        - Exit if can buy back for 50% of premium received
        - Exit if position reaches 80% of max loss
        - Exit early if threatened by underlying movement
        """
        spread_info = self.spread_positions.get(position.position_id)
        if not spread_info:
            return None

        spread_type = spread_info["spread_type"]
        net_premium = spread_info["net_premium"]
        max_profit = spread_info["max_profit"]
        max_loss = spread_info["max_loss"]
        entry_time = spread_info["entry_time"]

        # Calculate current P&L as percentage
        current_pnl = position.unrealized_pnl

        if spread_type == "DEBIT_SPREAD":
            # For debit spreads, we paid premium (negative)
            premium_paid = abs(net_premium)

            # Check profit target (70% of max profit)
            profit_target_pct = getattr(self.config, "debit_spread_tp_pct", 70)
            profit_target = max_profit * (profit_target_pct / 100.0)

            if current_pnl >= profit_target:
                logger.info(
                    "Debit spread profit target hit",
                    position_id=position.position_id,
                    current_pnl=current_pnl,
                    profit_target=profit_target,
                    pct_of_max=f"{(current_pnl / max_profit) * 100:.1f}%",
                )
                return ExitSignal(
                    position.position_id,
                    ExitReason.TAKE_PROFIT_1,
                    urgency="NORMAL",
                    details={
                        "spread_type": spread_type,
                        "profit_pct": (current_pnl / premium_paid) * 100,
                        "max_profit_pct": (current_pnl / max_profit) * 100,
                    },
                )

            # Check stop loss (50% of premium paid)
            stop_pct = getattr(self.config, "debit_spread_stop_pct", 50)
            stop_loss = -premium_paid * (stop_pct / 100.0)

            if current_pnl <= stop_loss:
                logger.warning(
                    "Debit spread stop loss hit",
                    position_id=position.position_id,
                    current_pnl=current_pnl,
                    stop_loss=stop_loss,
                    loss_pct=f"{(current_pnl / premium_paid) * 100:.1f}%",
                )
                return ExitSignal(
                    position.position_id,
                    ExitReason.STOP_LOSS,
                    urgency="URGENT",
                    details={
                        "spread_type": spread_type,
                        "loss_pct": (current_pnl / premium_paid) * 100,
                    },
                )

            # Time-based exit for debit spreads
            timeout_min = getattr(self.config, "debit_spread_timeout_min", 20)
            time_held = (current_time - entry_time).total_seconds() / 60

            if time_held >= timeout_min:
                # Exit if position not profitable after timeout
                if current_pnl <= 0:
                    logger.info(
                        "Debit spread timeout exit",
                        position_id=position.position_id,
                        time_held_min=time_held,
                        current_pnl=current_pnl,
                    )
                    return ExitSignal(
                        position.position_id,
                        ExitReason.TIME_STOP,
                        urgency="NORMAL",
                        details={
                            "spread_type": spread_type,
                            "time_held_min": time_held,
                            "reason": "Not profitable after timeout",
                        },
                    )

        elif spread_type == "CREDIT_SPREAD":
            # For credit spreads, we received premium (positive)
            premium_received = net_premium

            # Check if can buy back for 50% profit
            profit_target_pct = 50
            profit_target = premium_received * (profit_target_pct / 100.0)

            if current_pnl >= profit_target:
                logger.info(
                    "Credit spread profit target hit",
                    position_id=position.position_id,
                    current_pnl=current_pnl,
                    profit_target=profit_target,
                )
                return ExitSignal(
                    position.position_id,
                    ExitReason.TAKE_PROFIT_1,
                    urgency="NORMAL",
                    details={
                        "spread_type": spread_type,
                        "profit_pct": (current_pnl / premium_received) * 100,
                    },
                )

            # Check if approaching max loss
            stop_loss = max_loss * 0.8  # Exit at 80% of max loss

            if current_pnl <= -stop_loss:
                logger.warning(
                    "Credit spread stop loss hit",
                    position_id=position.position_id,
                    current_pnl=current_pnl,
                    stop_loss=-stop_loss,
                )
                return ExitSignal(
                    position.position_id,
                    ExitReason.STOP_LOSS,
                    urgency="URGENT",
                    details={
                        "spread_type": spread_type,
                        "loss_pct": (current_pnl / max_loss) * 100,
                    },
                )

        return None

    def _check_profit_protection(self, position: Position) -> Optional[ExitSignal]:
        """
        Protect profits by tightening stops after hitting milestones.

        Example: If position is up 2%, move stop to breakeven.
                 If position is up 5%, move stop to 3%.
        """
        if position.unrealized_pnl <= 0:
            return None

        position_id = position.position_id
        pnl_pct = (position.unrealized_pnl / abs(position.entry_price * position.quantity)) * 100

        # Define profit milestones (can be configured)
        milestones = [
            (2.0, 0.0),  # At 2% profit, move stop to breakeven
            (5.0, 3.0),  # At 5% profit, move stop to 3%
            (10.0, 7.0),  # At 10% profit, move stop to 7%
        ]

        # Track which milestones we've hit
        if position_id not in self.profit_milestones:
            self.profit_milestones[position_id] = []

        for milestone_pct, new_stop_pct in milestones:
            if pnl_pct >= milestone_pct and milestone_pct not in self.profit_milestones[position_id]:
                # Hit a new milestone
                self.profit_milestones[position_id].append(milestone_pct)

                # Calculate new stop price
                if position.side == SignalSide.LONG:
                    new_stop = position.entry_price * (1 + new_stop_pct / 100)
                    if new_stop > position.stop_loss:
                        position.stop_loss = new_stop
                        logger.info(
                            "Profit protection: Stop tightened",
                            position_id=position_id,
                            milestone_pct=milestone_pct,
                            new_stop=new_stop,
                            pnl_pct=pnl_pct,
                        )
                else:  # SHORT
                    new_stop = position.entry_price * (1 - new_stop_pct / 100)
                    if new_stop < position.stop_loss:
                        position.stop_loss = new_stop
                        logger.info(
                            "Profit protection: Stop tightened",
                            position_id=position_id,
                            milestone_pct=milestone_pct,
                            new_stop=new_stop,
                            pnl_pct=pnl_pct,
                        )

        return None

    def check_exits(
        self,
        positions: List[Position],
        market_data: Dict,
        current_time: datetime,
        daily_pnl_pct: float,
        net_liquid: float,
    ) -> List[ExitSignal]:
        """
        Enhanced exit checking with spread-specific and profit protection logic.
        """
        exit_signals = []

        for position in positions:
            if not position.is_open:
                continue

            # First check spread-specific exits
            spread_exit = self._check_spread_exits(position, current_time)
            if spread_exit:
                exit_signals.append(spread_exit)
                continue

            # Apply profit protection
            self._check_profit_protection(position)

        # Call parent class for standard exit checks
        standard_exits = super().check_exits(
            positions, market_data, current_time, daily_pnl_pct, net_liquid
        )
        exit_signals.extend(standard_exits)

        return exit_signals

    def on_position_closed(self, position_id: str) -> None:
        """Clean up tracking when position is closed"""
        super().on_position_closed(position_id)
        self.profit_milestones.pop(position_id, None)
        self.spread_positions.pop(position_id, None)
        logger.debug("Enhanced exit tracking cleared", position_id=position_id)
