"""Backtesting engine using historical data"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import structlog

from packages.core.config import app_config
from packages.core.execution import ExecutionEngine, OrderResult
from packages.core.historical_data import HistoricalDataLoader
from packages.core.indicators import IndicatorCalculator
from packages.core.models import Bar, Position, PositionStatus, Signal, SignalSide, Tick
from packages.core.paper_simulator import PaperSimulator
from packages.core.risk import PortfolioRisk, RiskManager
from packages.core.strategies import Strategy
from packages.core.strategies.base import StrategyContext

logger = structlog.get_logger(__name__)


class BacktestEngine:
    """
    Backtesting engine that replays historical data through strategies.
    
    Features:
    - Historical data replay
    - Strategy signal generation
    - Paper execution simulation
    - P&L tracking
    - Performance metrics
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000,  # 10 lakh
        data_dir: str = "docs/NSE OPINONS DATA"
    ):
        self.initial_capital = initial_capital
        self.data_loader = HistoricalDataLoader(data_dir)
        
        # State
        self.current_capital = initial_capital
        self.positions: List[Position] = []
        self.closed_trades: List[Dict] = []
        self.signals_generated: List[Signal] = []
        
        # Simulators
        self.paper_sim = PaperSimulator(
            slippage_bps=app_config.risk.slippage_bps,
            fees_per_order=app_config.risk.fees_per_order
        )
        
        self.risk_manager = RiskManager(app_config.risk)
        
        # Indicator calculator for backtesting
        self.indicator_calc = IndicatorCalculator(
            atr_period=14,
            rsi_period=14,
            adx_period=14,
            ema_fast=34,
            ema_slow=89,
            bb_period=20,
            bb_std=2.0
        )
        
        # Performance tracking
        self.daily_pnl: Dict[datetime, float] = {}
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
    
    def run_backtest(
        self,
        strategies: List[Strategy],
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        strikes: Optional[List[float]] = None
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            strategies: List of strategies to test
            symbol: NIFTY or BANKNIFTY
            start_date: Backtest start date
            end_date: Backtest end date
            strikes: Specific strikes to test (None for ATM)
        
        Returns:
            Backtest results dictionary
        """
        logger.info(
            "Starting backtest",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital
        )
        
        # Get date range
        current_date = start_date
        
        # Get strikes if not provided
        if strikes is None:
            strikes = self.data_loader.get_atm_strikes(symbol, start_date, num_strikes=5)
        
        logger.info(f"Testing {len(strikes)} strikes: {strikes}")
        
        # Iterate through dates
        while current_date <= end_date:
            # Skip weekends (simplified - in production, check actual trading days)
            if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current_date += timedelta(days=1)
                continue
            
            # Process day
            self._process_day(strategies, symbol, current_date, strikes)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Calculate final metrics
        results = self._calculate_results()
        
        logger.info(
            "Backtest completed",
            total_trades=len(self.closed_trades),
            final_capital=results['final_capital'],
            total_return=results['total_return_pct']
        )
        
        return results
    
    def _process_day(
        self,
        strategies: List[Strategy],
        symbol: str,
        date: datetime,
        strikes: List[float]
    ):
        """Process a single trading day"""
        logger.debug(f"Processing {date.strftime('%Y-%m-%d')}")
        
        # Get options chain for the day
        try:
            chain = self.data_loader.get_options_chain(symbol, date)
        except Exception as e:
            logger.warning(f"Failed to load data for {date}: {e}")
            return
        
        if chain.empty:
            return
        
        # Get underlying value
        underlying_value = chain['Underlying Value'].iloc[0] if 'Underlying Value' in chain.columns else None
        
        # Process each strike
        for strike in strikes:
            # Get CE and PE data
            ce_data = chain[(chain['Strike Price'] == strike) & (chain['Option type'] == 'CE')]
            pe_data = chain[(chain['Strike Price'] == strike) & (chain['Option type'] == 'PE')]
            
            if ce_data.empty and pe_data.empty:
                continue
            
            # Convert to bars (for strategies that need OHLC)
            if not ce_data.empty:
                ce_bars = self.data_loader.convert_to_bars(ce_data, symbol, strike, 'CE')
                # Attach technical indicators to bars
                ce_bars = self._attach_indicators(ce_bars)
                ce_tick = self.data_loader.convert_to_ticks(ce_data, symbol, strike, 'CE')
                
                # Generate signals for CE
                for strategy in strategies:
                    if not strategy.enabled:
                        continue
                    
                    signals = self._generate_signals(
                        strategy,
                        symbol,
                        strike,
                        'CE',
                        date,
                        ce_bars,
                        ce_tick[0] if ce_tick else None,
                        underlying_value
                    )
                    
                    # Execute signals
                    for signal in signals:
                        self._execute_signal(signal, date)
            
            # Same for PE
            if not pe_data.empty:
                pe_bars = self.data_loader.convert_to_bars(pe_data, symbol, strike, 'PE')
                # Attach technical indicators to bars
                pe_bars = self._attach_indicators(pe_bars)
                pe_tick = self.data_loader.convert_to_ticks(pe_data, symbol, strike, 'PE')
                
                for strategy in strategies:
                    if not strategy.enabled:
                        continue
                    
                    signals = self._generate_signals(
                        strategy,
                        symbol,
                        strike,
                        'PE',
                        date,
                        pe_bars,
                        pe_tick[0] if pe_tick else None,
                        underlying_value
                    )
                    
                    for signal in signals:
                        self._execute_signal(signal, date)
        
        # Update existing positions
        self._update_positions(date, chain)
        
        # Check exits
        self._check_exits(date)
        
        # Update daily P&L
        self._update_daily_pnl(date)
    
    def _attach_indicators(self, bars: List[Bar]) -> List[Bar]:
        """
        Calculate and attach technical indicators to bars.
        
        This is critical for backtesting - strategies require indicators
        (RSI, ATR, MACD, Bollinger Bands, VWAP, etc.) to generate signals.
        
        Args:
            bars: List of Bar objects with OHLCV data
            
        Returns:
            List of Bar objects with indicators attached
        """
        if not bars or len(bars) < 50:  # Need minimum bars for indicators
            logger.debug(f"Skipping indicator calculation: only {len(bars)} bars available")
            return bars
        
        try:
            # Convert bars to DataFrame for indicator calculation
            df = pd.DataFrame([
                {
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume
                }
                for bar in bars
            ])
            
            # Calculate indicators for the entire dataset first (more efficient)
            # Then attach to each bar
            all_indicators = self.indicator_calc.compute_all(df)
            
            # For rolling indicators, calculate per bar with lookback
            for i in range(len(bars)):
                bar = bars[i]
                
                # Get lookback window (need at least 50 bars for all indicators)
                start_idx = max(0, i - 50)
                end_idx = i + 1
                window_df = df.iloc[start_idx:end_idx]
                
                if len(window_df) < 26:  # Need at least 26 for MACD slow period
                    continue
                
                # Compute all indicators for this window
                indicators = self.indicator_calc.compute_all(window_df)
                
                # Attach indicators to current bar
                bar.vwap = indicators.get("vwap")
                bar.atr = indicators.get("atr")
                bar.rsi = indicators.get("rsi")
                bar.adx = indicators.get("adx")
                bar.ema_fast = indicators.get("ema_fast")
                bar.ema_slow = indicators.get("ema_slow")
                bar.supertrend = indicators.get("supertrend")
                bar.supertrend_direction = indicators.get("supertrend_direction")
                bar.macd = indicators.get("macd")
                bar.macd_signal = indicators.get("macd_signal")
                bar.macd_histogram = indicators.get("macd_histogram")
                bar.bb_upper = indicators.get("bb_upper")
                bar.bb_middle = indicators.get("bb_middle")
                bar.bb_lower = indicators.get("bb_lower")
                # New indicators for top 10 strategies
                bar.stoch_k = indicators.get("stoch_k")
                bar.stoch_d = indicators.get("stoch_d")
                bar.cci = indicators.get("cci")
                bar.sar = indicators.get("sar")
                bar.ichi_tenkan = indicators.get("ichi_tenkan")
                bar.ichi_kijun = indicators.get("ichi_kijun")
                bar.ichi_senkou_a = indicators.get("ichi_senkou_a")
                bar.ichi_senkou_b = indicators.get("ichi_senkou_b")
                bar.pivot = indicators.get("pivot")
                bar.pivot_r1 = indicators.get("pivot_r1")
                bar.pivot_r2 = indicators.get("pivot_r2")
                bar.pivot_s1 = indicators.get("pivot_s1")
                bar.pivot_s2 = indicators.get("pivot_s2")
                # Donchian channels (if not already set)
                if not hasattr(bar, 'dc_upper') or bar.dc_upper is None:
                    bar.dc_upper = indicators.get("dc_upper")
                    bar.dc_lower = indicators.get("dc_lower")
            
            # Count how many bars got indicators
            bars_with_indicators = sum(1 for b in bars if b.rsi is not None)
            logger.debug(f"Attached indicators to {bars_with_indicators}/{len(bars)} bars")
            return bars
            
        except Exception as e:
            logger.warning(f"Failed to attach indicators: {e}", exc_info=True)
            return bars  # Return bars without indicators if calculation fails
    
    def _generate_signals(
        self,
        strategy: Strategy,
        symbol: str,
        strike: float,
        option_type: str,
        date: datetime,
        bars: List,
        tick: Optional,
        underlying_value: float
    ) -> List[Signal]:
        """Generate signals from a strategy"""
        # Create mock instrument
        from packages.core.models import Instrument, InstrumentType
        
        inst_type = InstrumentType.CE if option_type == 'CE' else InstrumentType.PE
        
        instrument = Instrument(
            token=hash(f"{symbol}_{strike}_{option_type}") % 1000000,
            symbol=symbol,
            tradingsymbol=f"{symbol}{int(strike)}{option_type}",
            exchange="NFO",
            instrument_type=inst_type,
            strike=strike,
            lot_size=50 if symbol == "NIFTY" else 25,
            tick_size=0.05
        )
        
        # Create strategy context with backtest mode enabled
        context = StrategyContext(
            timestamp=date,
            instrument=instrument,
            latest_tick=tick,
            bars_5s=bars[-20:] if len(bars) >= 20 else bars,  # Last 20 bars
            bars_1s=bars[-60:] if len(bars) >= 60 else bars,  # Last 60 for 1s
            net_liquid=self.current_capital,
            available_margin=self.current_capital * 0.8,
            open_positions=len([p for p in self.positions if p.is_open]),
            backtest_mode=True  # Enable relaxed filters for backtesting
        )
        
        # Generate signals
        try:
            signals = strategy.generate_signals(context)
            self.signals_generated.extend(signals)
            return signals
        except Exception as e:
            logger.warning(f"Strategy {strategy.name} failed: {e}")
            return []
    
    def _execute_signal(self, signal: Signal, date: datetime):
        """Execute a trading signal"""
        # Check risk
        portfolio_risk = self._get_portfolio_risk()
        
        risk_check = self.risk_manager.check_signal(signal, portfolio_risk)
        
        if not risk_check.approved:
            logger.debug(f"Signal rejected: {risk_check.reasons}")
            return
        
        # Simulate order
        quantity = risk_check.position_size
        
        order = self.paper_sim.simulate_order(
            instrument_token=signal.instrument.token,
            instrument_symbol=signal.instrument.tradingsymbol,
            side="BUY" if signal.side == SignalSide.LONG else "SELL",
            quantity=quantity,
            order_type="MARKET",
            current_market_price=signal.entry_price
        )
        
        # Open position
        position = self.paper_sim.open_position(
            signal.instrument,
            order,
            signal.side,
            signal.stop_loss,
            signal.take_profit_1,
            signal.take_profit_2
        )
        
        # Update risk amount
        position.risk_amount = signal.stop_distance * quantity
        
        self.positions.append(position)
        
        logger.info(
            f"Position opened: {signal.instrument.tradingsymbol}",
            side=signal.side.value,
            quantity=quantity,
            entry_price=order.average_price
        )
    
    def _update_positions(self, date: datetime, chain: pd.DataFrame):
        """Update position P&L with current market prices"""
        for position in self.positions:
            if not position.is_open:
                continue
            
            # Find current price from chain
            strike = position.instrument.strike
            option_type = 'CE' if position.instrument.instrument_type.value == 'CE' else 'PE'
            
            row = chain[
                (chain['Strike Price'] == strike) &
                (chain['Option type'] == option_type)
            ]
            
            if not row.empty:
                current_price = row.iloc[0]['LTP'] if pd.notna(row.iloc[0]['LTP']) else row.iloc[0]['Close']
                position.current_price = current_price
                position.update_pnl()
    
    def _check_exits(self, date: datetime):
        """Check exit conditions for positions"""
        from packages.core.exits import ExitManager, ExitReason
        
        exit_manager = ExitManager(app_config.exits)
        
        # Get options chain for current prices (use symbol from first position)
        chain = None
        if self.positions:
            first_pos = self.positions[0]
            symbol = first_pos.instrument.symbol
            try:
                chain = self.data_loader.get_options_chain(symbol, date)
            except Exception as e:
                logger.debug(f"Could not load chain for exits: {e}")
        
        # Create market data dict with actual tick/bar data
        market_data = {}
        for position in self.positions:
            if position.is_open:
                # Get current price from chain or use entry price
                current_price = position.entry_price
                if chain is not None and not chain.empty:
                    strike = position.instrument.strike
                    option_type = 'CE' if position.instrument.instrument_type.value == 'CE' else 'PE'
                    row = chain[(chain['Strike Price'] == strike) & (chain['Option type'] == option_type)]
                    if not row.empty:
                        current_price = row.iloc[0]['LTP'] if pd.notna(row.iloc[0]['LTP']) else row.iloc[0]['Close']
                
                # Create a simple tick object
                tick = Tick(
                    token=position.instrument.token,
                    last_price=current_price,
                    timestamp=date
                )
                bars = []  # Bars not needed for exit checks in backtest
                market_data[position.instrument.token] = (tick, bars)
        
        # Check exits
        exit_signals = exit_manager.check_exits(
            self.positions,
            market_data,
            date,
            self._get_daily_pnl_pct(),
            self.current_capital
        )
        
        # Execute exits
        for exit_signal in exit_signals:
            position = next(
                (p for p in self.positions if p.position_id == exit_signal.position_id),
                None
            )
            if position:
                # Close position using paper simulator
                exit_order = self.paper_sim.close_position(
                    position,
                    position.current_price,
                    exit_signal.reason.value
                )

                # Record trade
                trade = {
                    "entry_date": position.entry_time,
                    "exit_date": date,
                    "instrument": position.instrument.tradingsymbol,
                    "side": position.side.value,
                    "quantity": position.quantity,
                    "entry_price": position.entry_price,
                    "exit_price": exit_order.average_price,
                    "pnl": position.realized_pnl or 0.0,
                    "exit_reason": exit_signal.reason.value
                }

                self.closed_trades.append(trade)

                # Update capital
                self.current_capital += position.realized_pnl or 0.0
                
                self.closed_trades.append(trade)
                
                # Update capital
                self.current_capital += position.realized_pnl or 0.0
    
    def _get_portfolio_risk(self) -> PortfolioRisk:
        """Get current portfolio risk state"""
        total_risk = sum([p.risk_amount for p in self.positions if p.is_open])
        unrealized_pnl = sum([p.unrealized_pnl for p in self.positions if p.is_open])
        
        return PortfolioRisk(
            net_liquid=self.current_capital,
            used_margin=total_risk * 0.5,  # Simplified
            available_margin=self.current_capital * 0.8,
            open_positions=[p for p in self.positions if p.is_open],
            total_risk_amount=total_risk,
            unrealized_pnl=unrealized_pnl,
            realized_pnl_today=sum([t.get('pnl', 0) for t in self.closed_trades]),
            daily_pnl=unrealized_pnl + sum([t.get('pnl', 0) for t in self.closed_trades]),
            daily_loss_limit=-self.initial_capital * 0.025,
            max_portfolio_heat=self.initial_capital * 0.02
        )
    
    def _update_daily_pnl(self, date: datetime):
        """Update daily P&L tracking"""
        realized = sum([t.get('pnl', 0) for t in self.closed_trades])
        unrealized = sum([p.unrealized_pnl for p in self.positions if p.is_open])
        
        self.daily_pnl[date] = realized + unrealized
        
        # Update drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _get_daily_pnl_pct(self) -> float:
        """Get daily P&L as percentage"""
        if self.initial_capital > 0:
            return ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        return 0.0
    
    def _calculate_results(self) -> Dict:
        """Calculate backtest performance metrics"""
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        wins = [t for t in self.closed_trades if t.get('pnl', 0) > 0]
        losses = [t for t in self.closed_trades if t.get('pnl', 0) <= 0]
        
        win_rate = (len(wins) / len(self.closed_trades) * 100) if self.closed_trades else 0.0
        
        avg_win = sum([t['pnl'] for t in wins]) / len(wins) if wins else 0.0
        avg_loss = sum([t['pnl'] for t in losses]) / len(losses) if losses else 0.0
        
        profit_factor = abs(sum([t['pnl'] for t in wins]) / sum([t['pnl'] for t in losses])) if losses and sum([t['pnl'] for t in losses]) != 0 else 0.0
        
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.current_capital,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "max_drawdown_pct": self.max_drawdown * 100,
            "total_trades": len(self.closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "largest_win": max([t['pnl'] for t in wins]) if wins else 0.0,
            "largest_loss": min([t['pnl'] for t in losses]) if losses else 0.0,
            "signals_generated": len(self.signals_generated),
            "daily_pnl": self.daily_pnl
        }

