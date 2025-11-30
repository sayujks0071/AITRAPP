"""Risk management and position sizing"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from packages.core.config import RiskConfig
from packages.core.models import (
    Instrument,
    Position,
    RiskCheckResult,
    Signal,
    SignalSide,
    AssetType,
)

logger = structlog.get_logger(__name__)


@dataclass
class PortfolioRisk:
    """Current portfolio risk metrics"""
    net_liquid: float
    used_margin: float
    available_margin: float
    
    # Positions
    open_positions: List[Position]
    total_risk_amount: float  # Sum of all position risks
    
    # P&L
    unrealized_pnl: float
    realized_pnl_today: float
    daily_pnl: float
    
    # Limits
    daily_loss_limit: float
    max_portfolio_heat: float
    
    @property
    def portfolio_heat_pct(self) -> float:
        """Portfolio heat as percentage of net liquid"""
        if self.net_liquid > 0:
            return (self.total_risk_amount / self.net_liquid) * 100
        return 0.0
    
    @property
    def daily_pnl_pct(self) -> float:
        """Daily PnL as percentage of net liquid"""
        if self.net_liquid > 0:
            return (self.daily_pnl / self.net_liquid) * 100
        return 0.0
    
    @property
    def is_daily_loss_breached(self) -> bool:
        """Check if daily loss limit is breached"""
        return self.daily_pnl < self.daily_loss_limit
    
    @property
    def is_heat_limit_breached(self) -> bool:
        """Check if portfolio heat limit is breached"""
        return self.portfolio_heat_pct >= self.max_portfolio_heat
    
    @property
    def can_take_new_position(self) -> bool:
        """Check if new position can be taken"""
        return not (self.is_daily_loss_breached or self.is_heat_limit_breached)


class RiskManager:
    """
    Manages risk for trading operations.
    
    Responsibilities:
    - Validate signals against risk limits
    - Calculate position sizes
    - Monitor portfolio heat
    - Enforce daily loss limits
    - Handle lot sizing and freeze quantities
    """
    
    def __init__(self, config: RiskConfig):
        self.config = config

        # Daily tracking
        self.daily_start_capital: Optional[float] = None
        self.trades_today = 0

        # Per-strategy capital caps (set by allocator)
        self.strategy_caps: Dict[str, float] = {}

        # SEBI Compliance: Per-strategy PnL tracking
        self.strategy_pnl: Dict[str, float] = {}  # strategy_name -> cumulative PnL
    
    def check_signal(
        self,
        signal: Signal,
        portfolio_risk: PortfolioRisk
    ) -> RiskCheckResult:
        """
        Check if a signal passes risk criteria.

        Args:
            signal: Trading signal to check
            portfolio_risk: Current portfolio risk state

        Returns:
            RiskCheckResult with approval status and position size
        """
        reasons = []

        # 0a. SEBI Compliance: Check strategy-wise loss limit
        strategy_name = signal.strategy_name
        strategy_pnl = self.get_strategy_pnl(strategy_name)
        max_loss = portfolio_risk.net_liquid * (self.config.max_loss_per_strategy_pct / 100)

        if strategy_pnl < max_loss:
            reasons.append(
                f"Strategy {strategy_name} loss {strategy_pnl:.2f} exceeds limit {max_loss:.2f}"
            )
            logger.warning(
                "❌ RISK VETO: STRATEGY_LOSS_LIMIT",
                strategy=strategy_name,
                pnl=strategy_pnl,
                limit=max_loss
            )
            return RiskCheckResult(approved=False, reasons=reasons)

        # 0. MCX safety: stop distance must clear tick size
        if signal.instrument and signal.instrument.exchange == "MCX":
            tick = float(signal.instrument.tick_size or 0.05)
            if signal.stop_distance < tick * 0.5:
                reasons.append(
                    f"Stop distance {signal.stop_distance:.4f} too tight vs tick {tick:.4f} for MCX"
                )
                return RiskCheckResult(approved=False, reasons=reasons)

        # 0b. Liquidity guards (spread/volume), only if data present
        liq_rejection = self._check_liquidity(signal)
        if liq_rejection:
            reasons.append(liq_rejection)
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 1. Check daily loss limit
        if portfolio_risk.is_daily_loss_breached:
            reasons.append(f"Daily loss limit breached: {portfolio_risk.daily_pnl_pct:.2f}%")
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 2. Check portfolio heat limit
        if portfolio_risk.is_heat_limit_breached:
            reasons.append(f"Portfolio heat limit breached: {portfolio_risk.portfolio_heat_pct:.2f}%")
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 3. Calculate position size
        position_size = self.calculate_position_size(
            signal=signal,
            net_liquid=portfolio_risk.net_liquid,
            instrument=signal.instrument
        )
        
        if position_size <= 0:
            reasons.append("Position size calculated as zero or negative")
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 4. Check per-trade risk
        trade_risk_amount = signal.stop_distance * position_size
        trade_risk_pct = (trade_risk_amount / portfolio_risk.net_liquid) * 100
        
        if trade_risk_pct > self.config.per_trade_risk_pct:
            reasons.append(
                f"Per-trade risk {trade_risk_pct:.2f}% exceeds limit {self.config.per_trade_risk_pct}%"
            )
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 5. Check if adding this risk breaches portfolio heat
        new_total_risk = portfolio_risk.total_risk_amount + trade_risk_amount
        new_heat_pct = (new_total_risk / portfolio_risk.net_liquid) * 100
        
        if new_heat_pct > self.config.max_portfolio_heat_pct:
            reasons.append(
                f"Portfolio heat limit breached: new heat {new_heat_pct:.2f}% would exceed limit {self.config.max_portfolio_heat_pct}%"
            )
            return RiskCheckResult(approved=False, reasons=reasons)
        
        # 6. Check freeze quantity (for F&O)
        if signal.instrument.freeze_quantity:
            if position_size > signal.instrument.freeze_quantity:
                reasons.append(
                    f"Position size {position_size} exceeds freeze quantity {signal.instrument.freeze_quantity}"
                )
                # Reduce to freeze quantity
                position_size = signal.instrument.freeze_quantity
                logger.warning(
                    "Position size capped at freeze quantity",
                    instrument=signal.instrument.tradingsymbol,
                    size=position_size
                )
        
        # 7. Crypto-specific checks
        if signal.instrument.asset_type == AssetType.CRYPTO:
            crypto_check = self._check_crypto_requirements(signal, position_size)
            if not crypto_check["approved"]:
                reasons.extend(crypto_check["reasons"])
                return RiskCheckResult(approved=False, reasons=reasons)
        
        # 8. Check available margin (skip for crypto spot - no margin)
        if signal.instrument.asset_type != AssetType.CRYPTO:
            estimated_margin = self.estimate_margin_required(
                signal.instrument,
                position_size,
                signal.entry_price
            )
            
            if estimated_margin > portfolio_risk.available_margin:
                reasons.append(
                    f"Insufficient margin: required {estimated_margin:.0f}, available {portfolio_risk.available_margin:.0f}"
                )
                return RiskCheckResult(approved=False, reasons=reasons)
        
        # All checks passed
        logger.info(
            "Risk check passed",
            instrument=signal.instrument.tradingsymbol,
            size=position_size,
            risk_pct=trade_risk_pct,
            new_heat_pct=new_heat_pct
        )
        
        return RiskCheckResult(
            approved=True,
            reasons=["All risk checks passed"],
            risk_pct=trade_risk_pct,
            position_size=position_size
        )
    
    def calculate_position_size(
        self,
        signal: Signal,
        net_liquid: float,
        instrument: Instrument
    ) -> int:
        """
        Calculate position size based on risk parameters.
        
        Formula:
        Position Size = (Capital * Risk%) / Stop Distance
        
        For F&O, round to lot sizes.
        
        Args:
            signal: Trading signal with entry and stop
            net_liquid: Net liquid capital
            instrument: Instrument details
        
        Returns:
            Position size in quantity (not lots)
        """
        if signal.stop_distance <= 0:
            logger.warning("Invalid stop distance", distance=signal.stop_distance)
            return 0
        
        # Calculate risk amount
        risk_amount = net_liquid * (self.config.per_trade_risk_pct / 100)
        
        # Calculate quantity
        quantity = risk_amount / signal.stop_distance
        
        # Apply max position size multiplier
        max_quantity = instrument.lot_size * self.config.max_position_size_multiplier
        quantity = min(quantity, max_quantity)
        
        # Round to lot size for F&O
        if instrument.lot_size > 1:
            lots = int(quantity / instrument.lot_size)
            lots = max(1, lots)  # At least 1 lot
            quantity = lots * instrument.lot_size
        else:
            # For equities, round down
            quantity = int(quantity)
        
        logger.debug(
            "Position size calculated",
            instrument=instrument.tradingsymbol,
            quantity=quantity,
            lots=quantity // instrument.lot_size if instrument.lot_size > 1 else quantity,
            risk_amount=risk_amount
        )
        
        return int(quantity)
    
    def estimate_margin_required(
        self,
        instrument: Instrument,
        quantity: int,
        price: float
    ) -> float:
        """
        Estimate margin required for a position.
        
        This is a simplified calculation. In production, use
        Kite's margin calculator API.
        
        Args:
            instrument: Instrument details
            quantity: Position quantity
            price: Entry price
        
        Returns:
            Estimated margin in INR
        """
        if instrument.is_equity:
            # CNC requires full capital
            return quantity * price
        
        elif instrument.is_future:
            # Futures require margin (approx 10-20% for indices, higher for stocks)
            # Use conservative 25%
            return quantity * price * 0.25
        
        elif instrument.is_option:
            # Options: Premium + SPAN + Exposure
            # For buying: Premium only
            # For selling: Premium + margin
            # Simplified: Premium * 5 for selling, Premium for buying
            return quantity * price * 5
        
        return quantity * price
    
    def estimate_fees(
        self,
        instrument: Instrument,
        quantity: int,
        entry_price: float,
        exit_price: float
    ) -> float:
        """
        Estimate trading fees for a round trip.
        
        Includes:
        - Brokerage
        - STT/CTT
        - Exchange charges
        - GST
        - SEBI charges
        - Stamp duty
        
        Args:
            instrument: Instrument details
            quantity: Position quantity
            entry_price: Entry price
            exit_price: Exit price
        
        Returns:
            Estimated total fees in INR
        """
        turnover = quantity * (entry_price + exit_price)
        
        # Simplified fee calculation (Zerodha-like structure)
        fees = 0.0
        is_mcx = instrument.exchange == "MCX"
        fees_per_order = self.config.mcx_fees_per_order if is_mcx else self.config.fees_per_order
        fees_per_leg = self.config.mcx_fees_per_option_leg if is_mcx else self.config.fees_per_option_leg
        
        # Brokerage: Rs 20 per order or 0.03% (equity delivery)
        if instrument.is_equity:
            fees += fees_per_order * 2  # Entry + Exit
        elif instrument.is_future or instrument.is_option:
            fees += fees_per_order * 2
            if instrument.is_option:
                fees += fees_per_leg * quantity
        
        # STT: 0.025% on sell side for equity delivery, 0.05% for futures
        if instrument.is_equity:
            fees += (exit_price * quantity) * 0.00025
        elif instrument.is_future:
            fees += turnover * 0.0001
        elif instrument.is_option:
            fees += (exit_price * quantity) * 0.00005
        
        # Transaction charges: ~0.00325% for NSE equity, ~0.002% for F&O
        if instrument.exchange in ["NSE", "BSE"]:
            fees += turnover * 0.0000325
        elif is_mcx:
            # MCX transaction charges slightly higher; conservative bump
            fees += turnover * 0.00005
        else:
            fees += turnover * 0.00002
        
        # GST on brokerage and transaction charges: 18%
        fees *= 1.18
        
        # SEBI charges: Rs 10 per crore
        fees += (turnover / 10000000) * 10
        
        # Stamp duty: 0.003% on buy side
        fees += (entry_price * quantity) * 0.00003
        
        return fees
    
    def update_portfolio_risk(
        self,
        net_liquid: float,
        positions: List[Position],
        realized_pnl_today: float
    ) -> PortfolioRisk:
        """
        Calculate current portfolio risk metrics.
        
        Args:
            net_liquid: Net liquid capital
            positions: Open positions
            realized_pnl_today: Realized P&L today
        
        Returns:
            PortfolioRisk object
        """
        # Initialize daily capital if needed
        if self.daily_start_capital is None:
            self.daily_start_capital = net_liquid
        
        # Calculate total risk
        total_risk = sum([pos.risk_amount for pos in positions if pos.is_open])
        
        # Calculate unrealized PnL
        unrealized_pnl = sum([pos.unrealized_pnl for pos in positions if pos.is_open])
        
        # Calculate daily PnL
        daily_pnl = realized_pnl_today + unrealized_pnl
        
        # Calculate limits
        daily_loss_limit = self.daily_start_capital * (self.config.daily_loss_stop_pct / 100)
        max_portfolio_heat = self.daily_start_capital * (self.config.max_portfolio_heat_pct / 100)
        
        # Estimate used margin (simplified)
        used_margin = sum([
            self.estimate_margin_required(pos.instrument, pos.quantity, pos.entry_price)
            for pos in positions if pos.is_open
        ])
        
        available_margin = net_liquid - used_margin
        
        portfolio_risk = PortfolioRisk(
            net_liquid=net_liquid,
            used_margin=used_margin,
            available_margin=available_margin,
            open_positions=positions,
            total_risk_amount=total_risk,
            unrealized_pnl=unrealized_pnl,
            realized_pnl_today=realized_pnl_today,
            daily_pnl=daily_pnl,
            daily_loss_limit=daily_loss_limit,
            max_portfolio_heat=max_portfolio_heat
        )
        
        return portfolio_risk

    def _check_liquidity(self, signal: Signal) -> Optional[str]:
        """
        Liquidity guard: spread/volume checks when available.
        Applies exchange-specific thresholds.
        """
        try:
            features = getattr(signal, "features", {}) or {}
            spread_pct = features.get("spread_pct") or getattr(signal, "spread_pct", None)
            volume = features.get("volume") or getattr(signal, "volume", None)

            # Fallback: derive spread_pct from bid/ask if provided in features
            if spread_pct is None:
                bid = features.get("bid")
                ask = features.get("ask")
                if bid and ask and bid > 0 and ask > 0 and ask >= bid:
                    mid = (bid + ask) / 2
                    if mid > 0:
                        spread_pct = ((ask - bid) / mid) * 100

            # Fallback: derive volume from bid/ask quantities if provided
            if volume is None:
                bid_qty = features.get("bid_qty") or 0
                ask_qty = features.get("ask_qty") or 0
                ltp_volume = features.get("ltp_volume") or 0
                derived_vol = max(ltp_volume, bid_qty + ask_qty)
                volume = derived_vol if derived_vol > 0 else None
            if spread_pct is None and volume is None:
                return None

            exch = ""
            if signal.instrument:
                exch = (signal.instrument.exchange or "").upper()
            is_mcx = exch == "MCX"

            max_spread = self.config.mcx_max_spread_pct if is_mcx else self.config.nse_max_spread_pct
            min_vol = self.config.mcx_min_volume if is_mcx else self.config.nse_min_volume

            if spread_pct is not None and spread_pct > max_spread:
                return f"Spread {spread_pct:.2f}% exceeds guard {max_spread:.2f}% ({'MCX' if is_mcx else 'NSE'})"
            if volume is not None and volume < min_vol:
                return f"Volume {volume} below guard {min_vol} ({'MCX' if is_mcx else 'NSE'})"
        except Exception as e:
            logger.debug("Liquidity guard check failed", error=str(e))
        return None
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters (call at start of day)"""
        self.daily_start_capital = None
        self.trades_today = 0
        self.strategy_pnl = {}  # Reset strategy PnL tracking
        logger.info("Daily risk counters reset")

    def get_strategy_pnl(self, strategy_name: str) -> float:
        """
        Get cumulative PnL for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Cumulative PnL in rupees (negative = loss)
        """
        return self.strategy_pnl.get(strategy_name, 0.0)

    def update_strategy_pnl(self, strategy_name: str, pnl_change: float) -> None:
        """
        Update PnL for a specific strategy (called when position closes).

        Args:
            strategy_name: Name of the strategy
            pnl_change: PnL change in rupees (positive = profit, negative = loss)
        """
        current = self.strategy_pnl.get(strategy_name, 0.0)
        self.strategy_pnl[strategy_name] = current + pnl_change
        logger.debug(
            "Strategy PnL updated",
            strategy=strategy_name,
            pnl_change=pnl_change,
            total_pnl=self.strategy_pnl[strategy_name]
        )
    
    def _check_crypto_requirements(
        self,
        signal: Signal,
        position_size: int
    ) -> Dict[str, Any]:
        """
        Check crypto-specific requirements:
        - Min notional (order value >= min_notional)
        - Precision (price/quantity rounding)
        - Spot-only (no leverage)
        - 24/7 guardrails (no market hours restrictions)
        
        Args:
            signal: Trading signal
            position_size: Calculated position size
        
        Returns:
            Dict with 'approved' bool and 'reasons' list
        """
        reasons = []
        
        # 1. Check min notional (if symbol_info available)
        # This is a placeholder - in production, would fetch from exchange
        min_notional_usd = 25.0  # Conservative default
        order_notional = signal.entry_price * position_size
        
        if order_notional < min_notional_usd:
            reasons.append(
                f"Crypto order notional {order_notional:.2f} USD < min_notional {min_notional_usd} USD"
            )
            return {"approved": False, "reasons": reasons}
        
        # 2. Precision check (would be enforced by exchange adapter)
        # Price and quantity will be rounded by exchange adapter
        
        # 3. Spot-only check (no leverage)
        # For spot, we only check available balance, not margin
        # This is handled in the main check_signal flow
        
        # 4. 24/7 guardrails
        # Crypto markets are 24/7, so no market hours check needed
        # But we can add volatility/spread checks here if needed
        
        return {"approved": True, "reasons": []}
    
    def can_enter(
        self,
        risk_cfg: RiskConfig,
        portfolio: PortfolioRisk,
        stop_dist: float,
        instrument: Instrument,
        price: float,
        capital: float
    ) -> tuple[bool, int]:
        """
        Hard gate check: can we enter this trade?
        
        Returns:
            (approved: bool, quantity: int)
        """
        # 1. Per-trade risk
        rupees_risk = capital * (risk_cfg.per_trade_risk_pct / 100)
        qty = max(1, int(rupees_risk / (stop_dist * instrument.lot_size * price) * instrument.lot_size))
        
        # Round to lot size
        if instrument.lot_size > 1:
            lots = max(1, int(qty / instrument.lot_size))
            qty = lots * instrument.lot_size
        
        # 2. Portfolio heat check
        open_risk = portfolio.total_risk_amount
        if (open_risk + rupees_risk) > capital * (risk_cfg.max_portfolio_heat_pct / 100):
            logger.warning("Portfolio heat limit would be breached",
                         current_heat=open_risk,
                         new_risk=rupees_risk,
                         limit=capital * (risk_cfg.max_portfolio_heat_pct / 100))
            return False, 0
        
        # 3. Daily loss stop
        if portfolio.realized_pnl_today <= -capital * (risk_cfg.daily_loss_stop_pct / 100):
            logger.warning("Daily loss stop breached",
                         daily_pnl=portfolio.realized_pnl_today,
                         limit=-capital * (risk_cfg.daily_loss_stop_pct / 100))
            return False, 0
        
        return True, qty
    
    def set_strategy_cap(self, strategy_name: str, max_capital_pct: float) -> None:
        """
        Set maximum capital percentage for a strategy (called by allocator).
        
        Args:
            strategy_name: Name of the strategy
            max_capital_pct: Maximum capital percentage (0.0 to 1.0)
        """
        self.strategy_caps[strategy_name] = max(0.0, min(1.0, max_capital_pct))
        logger.info(
            "Strategy cap updated",
            strategy=strategy_name,
            max_capital_pct=max_capital_pct
        )
    
    def get_strategy_cap(self, strategy_name: str) -> Optional[float]:
        """
        Get maximum capital percentage for a strategy.
        
        Args:
            strategy_name: Name of the strategy
        
        Returns:
            Max capital percentage or None if not set
        """
        return self.strategy_caps.get(strategy_name)
    
    def can_allocate(self, signal: Signal, max_capital_pct: Optional[float] = None) -> bool:
        """
        Check if a signal can be allocated capital.
        
        This is a simplified check that respects strategy caps.
        In production, would integrate with full risk checks.
        
        Args:
            signal: Trading signal
            max_capital_pct: Optional override for max capital %
        
        Returns:
            True if allocation is allowed
        """
        strategy_name = signal.strategy_name
        
        # Check strategy cap if set
        if strategy_name in self.strategy_caps:
            cap = self.strategy_caps[strategy_name]
            if cap <= 0.0:
                return False
            # In production, would check current allocation vs cap
            # For now, just check if cap > 0
        
        # If max_capital_pct provided, use it
        if max_capital_pct is not None:
            if max_capital_pct <= 0.0:
                return False
        
        return True
