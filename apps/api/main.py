"""FastAPI main application"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kiteconnect import KiteConnect
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from packages.core.config import app_config, settings
from packages.core.execution import ExecutionEngine
from packages.core.exits import ExitManager, ExitSignal
from packages.core.instruments import InstrumentManager
from packages.core.market_data import MarketDataStream
from packages.core.models import Position, PositionStatus, SystemState
from packages.core.risk import PortfolioRisk, RiskManager
from packages.core.strategies import ORBStrategy, TrendPullbackStrategy, OptionsRankerStrategy

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger(__name__)

# Global state
class AppState:
    """Application state"""
    kite: KiteConnect = None
    instrument_manager: InstrumentManager = None
    market_data_stream: MarketDataStream = None
    risk_manager: RiskManager = None
    exit_manager: ExitManager = None
    execution_engine: ExecutionEngine = None
    
    # Strategies
    strategies: Dict = {}
    
    # Positions
    positions: List[Position] = []
    
    # Control flags
    is_paused: bool = False
    is_market_open: bool = False
    
    # Performance metrics
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    realized_pnl_today: float = 0.0


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting AITRAPP", mode=settings.app_mode.value)
    
    # Initialize Kite Connect
    app_state.kite = KiteConnect(api_key=settings.kite_api_key)
    app_state.kite.set_access_token(settings.kite_access_token)
    
    # Initialize managers
    app_state.instrument_manager = InstrumentManager(
        app_state.kite,
        app_config.universe,
        settings
    )
    
    app_state.risk_manager = RiskManager(app_config.risk)
    app_state.exit_manager = ExitManager(app_config.exits)
    
    app_state.execution_engine = ExecutionEngine(
        app_state.kite,
        app_config.execution,
        settings
    )
    
    # Initialize market data stream
    app_state.market_data_stream = MarketDataStream(
        settings=settings,
        window_seconds=[1, 5]
    )
    
    # Sync instruments
    await app_state.instrument_manager.sync_instruments()
    await app_state.instrument_manager.sync_fo_ban_list()
    
    # Build universe
    universe_tokens = await app_state.instrument_manager.build_universe()
    logger.info(f"Universe: {len(universe_tokens)} instruments")
    
    # Initialize strategies
    for strategy_config in app_config.get_enabled_strategies():
        if strategy_config.name == "ORB":
            app_state.strategies["ORB"] = ORBStrategy(
                strategy_config.name,
                strategy_config.params
            )
        elif strategy_config.name == "TrendPullback":
            app_state.strategies["TrendPullback"] = TrendPullbackStrategy(
                strategy_config.name,
                strategy_config.params
            )
        elif strategy_config.name == "OptionsRanker":
            app_state.strategies["OptionsRanker"] = OptionsRankerStrategy(
                strategy_config.name,
                strategy_config.params
            )
    
    logger.info(f"Loaded {len(app_state.strategies)} strategies")
    
    # Start market data stream
    if settings.app_mode.value == "PAPER" or True:  # Always start in paper/dev
        app_state.market_data_stream.initialize()
        app_state.market_data_stream.start()
        
        # Subscribe to universe
        if universe_tokens:
            app_state.market_data_stream.subscribe(universe_tokens[:50])  # Limit for demo
    
    logger.info("AITRAPP started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AITRAPP")
    
    if app_state.market_data_stream:
        app_state.market_data_stream.stop()
    
    logger.info("AITRAPP stopped")


# Create FastAPI app
app = FastAPI(
    title="AITRAPP API",
    description="Autonomous Intelligent Trading Application",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics
if settings.enable_metrics:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# ===== API Models =====

class ModeChangeRequest(BaseModel):
    mode: str  # PAPER or LIVE
    confirmation: str = ""


class PositionResponse(BaseModel):
    position_id: str
    instrument: str
    side: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    pnl_pct: float


class SystemStateResponse(BaseModel):
    timestamp: str
    mode: str
    is_paused: bool
    is_market_open: bool
    positions_count: int
    trades_today: int
    win_rate: float
    daily_pnl: float


# ===== Control Endpoints =====

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mode": settings.app_mode.value,
        "is_paused": app_state.is_paused,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/mode")
async def change_mode(request: ModeChangeRequest):
    """
    Change application mode (PAPER <-> LIVE).
    
    LIVE mode requires explicit confirmation.
    """
    if request.mode not in ["PAPER", "LIVE"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be PAPER or LIVE.")
    
    if request.mode == "LIVE":
        if request.confirmation != "CONFIRM LIVE TRADING":
            raise HTTPException(
                status_code=403,
                detail="LIVE mode requires confirmation: 'CONFIRM LIVE TRADING'"
            )
        
        # Additional safety checks for LIVE mode
        if len(app_state.positions) > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot switch to LIVE mode with open positions. Close all positions first."
            )
        
        logger.warning("⚠️  SWITCHING TO LIVE MODE ⚠️")
    
    # Update mode
    settings.app_mode = request.mode
    app_config.mode = request.mode
    
    logger.info(f"Mode changed to {request.mode}")
    
    return {
        "status": "success",
        "mode": request.mode,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/pause")
async def pause_trading():
    """
    PAUSE trading: Stop new signals and cancel pending orders.
    Does NOT close existing positions (use /flatten for that).
    """
    app_state.is_paused = True
    
    logger.warning("🛑 TRADING PAUSED")
    
    return {
        "status": "paused",
        "timestamp": datetime.now().isoformat(),
        "message": "Trading paused. No new positions will be opened."
    }


@app.post("/resume")
async def resume_trading():
    """Resume trading after pause"""
    app_state.is_paused = False
    
    logger.info("▶️  TRADING RESUMED")
    
    return {
        "status": "resumed",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/flatten")
async def flatten_all():
    """
    KILL SWITCH: Close all positions immediately with market orders.
    Also pauses trading.
    """
    app_state.is_paused = True
    
    logger.critical("🚨 KILL SWITCH ACTIVATED - FLATTENING ALL POSITIONS")
    
    closed_count = 0
    errors = []
    
    for position in app_state.positions:
        if position.is_open:
            try:
                order = await app_state.execution_engine.close_position(
                    position,
                    reason="KILL_SWITCH"
                )
                if order:
                    position.status = PositionStatus.CLOSED
                    closed_count += 1
            except Exception as e:
                errors.append({
                    "position_id": position.position_id,
                    "error": str(e)
                })
                logger.error(f"Failed to close position {position.position_id}: {e}")
    
    return {
        "status": "flattened",
        "closed_positions": closed_count,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }


# ===== Data Endpoints =====

@app.get("/positions")
async def get_positions():
    """Get all open positions"""
    positions = [
        PositionResponse(
            position_id=pos.position_id,
            instrument=pos.instrument.tradingsymbol if pos.instrument else "UNKNOWN",
            side=pos.side.value,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            current_price=pos.current_price,
            unrealized_pnl=pos.unrealized_pnl,
            pnl_pct=pos.pnl_pct
        )
        for pos in app_state.positions if pos.is_open
    ]
    
    return {
        "positions": positions,
        "count": len(positions)
    }


@app.post("/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a specific position"""
    position = next((p for p in app_state.positions if p.position_id == position_id), None)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if not position.is_open:
        raise HTTPException(status_code=400, detail="Position already closed")
    
    try:
        order = await app_state.execution_engine.close_position(
            position,
            reason="MANUAL_CLOSE"
        )
        
        if order:
            position.status = PositionStatus.CLOSED
            
            return {
                "status": "success",
                "position_id": position_id,
                "order_id": order.order_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to place close order")
    
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state")
async def get_system_state():
    """Get current system state"""
    win_rate = 0.0
    if app_state.trades_today > 0:
        win_rate = (app_state.wins_today / app_state.trades_today) * 100
    
    return SystemStateResponse(
        timestamp=datetime.now().isoformat(),
        mode=settings.app_mode.value,
        is_paused=app_state.is_paused,
        is_market_open=app_state.is_market_open,
        positions_count=len([p for p in app_state.positions if p.is_open]),
        trades_today=app_state.trades_today,
        win_rate=win_rate,
        daily_pnl=app_state.realized_pnl_today
    )


@app.get("/orders")
async def get_orders():
    """Get all orders"""
    orders = app_state.execution_engine.orders.values()
    
    return {
        "orders": [
            {
                "order_id": order.order_id,
                "client_order_id": order.client_order_id,
                "timestamp": order.timestamp.isoformat(),
                "side": order.side,
                "quantity": order.quantity,
                "price": order.price,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity
            }
            for order in orders
        ],
        "count": len(orders)
    }


@app.post("/universe/reload")
async def reload_universe():
    """Reload trading universe"""
    try:
        await app_state.instrument_manager.sync_instruments()
        await app_state.instrument_manager.sync_fo_ban_list()
        universe_tokens = await app_state.instrument_manager.build_universe()
        
        return {
            "status": "success",
            "universe_size": len(universe_tokens),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to reload universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/strategies/reload")
async def reload_strategies():
    """Reload strategy configurations"""
    try:
        app_config.reload()
        
        # Reinitialize strategies
        app_state.strategies.clear()
        
        for strategy_config in app_config.get_enabled_strategies():
            if strategy_config.name == "ORB":
                app_state.strategies["ORB"] = ORBStrategy(
                    strategy_config.name,
                    strategy_config.params
                )
            elif strategy_config.name == "TrendPullback":
                app_state.strategies["TrendPullback"] = TrendPullbackStrategy(
                    strategy_config.name,
                    strategy_config.params
                )
            elif strategy_config.name == "OptionsRanker":
                app_state.strategies["OptionsRanker"] = OptionsRankerStrategy(
                    strategy_config.name,
                    strategy_config.params
                )
        
        return {
            "status": "success",
            "strategies_loaded": len(app_state.strategies),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to reload strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BacktestRequest(BaseModel):
    """Backtest request model"""
    symbol: str = "NIFTY"  # NIFTY or BANKNIFTY
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    initial_capital: float = 1000000
    strategy: str = "all"  # ORB, TrendPullback, OptionsRanker, or all


@app.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    Run backtest on historical data.
    
    This endpoint runs strategies on historical NSE options data
    and returns performance metrics.
    """
    try:
        from packages.core.backtest import BacktestEngine
        
        # Parse dates
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # Initialize strategies
        strategies = []
        
        if request.strategy == "all" or request.strategy == "ORB":
            orb_config = app_config.get_strategy_by_name("ORB")
            if orb_config:
                strategies.append(ORBStrategy("ORB", orb_config.params))
        
        if request.strategy == "all" or request.strategy == "TrendPullback":
            tp_config = app_config.get_strategy_by_name("TrendPullback")
            if tp_config:
                strategies.append(TrendPullbackStrategy("TrendPullback", tp_config.params))
        
        if request.strategy == "all" or request.strategy == "OptionsRanker":
            opt_config = app_config.get_strategy_by_name("OptionsRanker")
            if opt_config:
                strategies.append(OptionsRankerStrategy("OptionsRanker", opt_config.params))
        
        if not strategies:
            raise HTTPException(
                status_code=400,
                detail="No strategies configured. Check configs/app.yaml"
            )
        
        # Run backtest
        engine = BacktestEngine(
            initial_capital=request.initial_capital,
            data_dir="docs/NSE OPINONS DATA"
        )
        
        results = engine.run_backtest(
            strategies=strategies,
            symbol=request.symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "status": "success",
            "results": results,
            "trades": engine.closed_trades[:100],  # First 100 trades
            "timestamp": datetime.now().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Historical data not found: {e}")
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AITRAPP API",
        "version": "1.0.0",
        "mode": settings.app_mode.value,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
