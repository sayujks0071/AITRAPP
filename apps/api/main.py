"""FastAPI main application"""
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kiteconnect import KiteConnect
from prometheus_client import make_asgi_app, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse, Response, JSONResponse
from packages.core.metrics import get_metrics, metrics_app
from packages.core.redis_bus import RedisBus
from packages.core.oco import OCOManager
from packages.core.order_watcher import OrderWatcher
from packages.core.kite_client import KiteClient
from packages.storage.database import SessionLocal
from pydantic import BaseModel

from packages.core.config import app_config, settings
from packages.core.execution import ExecutionEngine
from packages.core.exits import ExitManager, ExitSignal
from packages.core.instruments import InstrumentManager
from packages.core.market_data import MarketDataStream
from packages.core.position_store import PositionStore
from packages.core.models import Position, PositionStatus, SystemState
from packages.core.orchestrator import TradingOrchestrator
from packages.core.risk import PortfolioRisk, RiskManager
from packages.core.hedging.delta_neutralizer import DeltaNeutralizer, DeltaNeutralizerConfig
from packages.core.ranker import SignalRanker
from packages.core.strategies import (
    ORBStrategy, TrendPullbackStrategy, OptionsRankerStrategy, Strategy,
    RegimeVolEngine, GammaScalper, CalendarArb, DispersionArb, TailShortVolOverlay,
    ExpiryShortStrangleV2, IntradayShortStrangleV1
)
from packages.core.strategies.trend_credit_spread_v1 import TrendCreditSpreadV1
from packages.core.strategies.strategy_allocator import StrategyAllocator

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
    ranker: SignalRanker = None
    orchestrator: TradingOrchestrator = None
    
    # Position store (canonical PnL/exposure source)
    position_store: PositionStore = None
    
    # Strategy allocator (capital allocation meta-layer)
    strategy_allocator: StrategyAllocator = None
    
    # Strategies
    strategies: Dict = {}
    strategy_list: List[Strategy] = []
    
    # Event engine (E1)
    event_engine: Any = None
    
    # Shared delta selector (for option strategies)
    delta_selector: Any = None
    
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
    
    # CRITICAL: Validate config coherence for LIVE mode
    if settings.app_mode.value == "LIVE":
        venue_name = app_config.venue.get("name", "UNKNOWN") if isinstance(app_config.venue, dict) else getattr(app_config.venue, "name", "UNKNOWN")
        strategy_names = [s.name for s in app_config.get_enabled_strategies()]
        
        # Verify NSE venue for LIVE mode
        if venue_name not in ["NSE", "NFO"]:
            logger.critical(
                "LIVE mode config validation FAILED",
                venue=venue_name,
                expected="NSE",
                config_path=app_config.config_path
            )
            raise ValueError(
                f"LIVE mode requires NSE venue, but loaded config has venue={venue_name}. "
                f"Config loaded from: {app_config.config_path}. "
                f"Set APP_CONFIG=configs/kite_day1_live.yaml to fix."
            )
        
        # Verify expected strategies are loaded
        expected_strategies = ["OptionsRanker"]  # Minimum required
        missing = [s for s in expected_strategies if s not in strategy_names]
        if missing:
            logger.critical(
                "LIVE mode missing required strategies",
                missing=missing,
                loaded=strategy_names,
                config_path=app_config.config_path
            )
            raise ValueError(
                f"LIVE mode missing required strategies: {missing}. "
                f"Loaded strategies: {strategy_names}. "
                f"Config loaded from: {app_config.config_path}. "
                f"Set APP_CONFIG=configs/kite_day1_live.yaml to fix."
            )
        
        logger.info(
            "LIVE mode config validation PASSED",
            venue=venue_name,
            strategies=strategy_names,
            config_path=app_config.config_path
        )
    
    # Clock skew check (fail if drift > 2s)
    import subprocess
    try:
        result = subprocess.run(
            ["bash", "scripts/check_ntp_drift.sh"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            logger.warning(f"Clock drift check failed: {result.stderr}")
            # Don't fail startup, but log warning
    except Exception as e:
        logger.warning(f"Could not check clock drift: {e}")
    
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
    
    # Initialize PositionStore (canonical source for positions/PnL)
    app_state.position_store = PositionStore()
    logger.info("PositionStore initialized")
    
    app_state.execution_engine = ExecutionEngine(
        app_state.kite,
        app_config.execution,
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
    strategy_list = []
    strategy_registry = {}  # For R1 meta-strategy
    
    for strategy_config in app_config.get_enabled_strategies():
        strategy = None
        if strategy_config.name == "ORB":
            strategy = ORBStrategy(strategy_config.name, strategy_config.params)
            app_state.strategies["ORB"] = strategy
            strategy_registry["ORB"] = strategy
        elif strategy_config.name == "TrendPullback":
            strategy = TrendPullbackStrategy(strategy_config.name, strategy_config.params)
            app_state.strategies["TrendPullback"] = strategy
            strategy_registry["TrendPullback"] = strategy
        elif strategy_config.name == "OptionsRanker":
            strategy = OptionsRankerStrategy(strategy_config.name, strategy_config.params)
            app_state.strategies["OptionsRanker"] = strategy
            strategy_registry["OptionsRanker"] = strategy
        elif strategy_config.name == "IronCondor":
            from packages.core.strategies import IronCondorStrategy
            strategy = IronCondorStrategy(strategy_config.name, strategy_config.params)
            app_state.strategies["IronCondor"] = strategy
            strategy_registry["IronCondor"] = strategy
        elif strategy_config.name == "RegimeVolEngine":
            # Load R1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            r1_config_path = Path("configs/regime_vol_engine.yaml")
            if r1_config_path.exists():
                with open(r1_config_path, "r") as f:
                    r1_config = yaml.safe_load(f)
                    strategy = RegimeVolEngine(
                        strategy_config.name,
                        r1_config.get("regime_vol_engine", {}),
                        strategy_registry=strategy_registry,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper()
                    )
                    app_state.strategies["RegimeVolEngine"] = strategy
                    strategy_registry["RegimeVolEngine"] = strategy
            else:
                logger.warning("RegimeVolEngine config not found, using default params")
                from packages.core.metrics_wrapper import MetricsWrapper
                strategy = RegimeVolEngine(
                    strategy_config.name,
                    strategy_config.params,
                    strategy_registry=strategy_registry,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper()
                )
                app_state.strategies["RegimeVolEngine"] = strategy
                strategy_registry["RegimeVolEngine"] = strategy
        elif strategy_config.name == "GammaScalper":
            # Load G1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            g1_config_path = Path("configs/gamma_scalper.yaml")
            if g1_config_path.exists():
                with open(g1_config_path, "r") as f:
                    g1_config = yaml.safe_load(f)
                    strategy = GammaScalper(
                        strategy_config.name,
                        g1_config.get("gamma_scalper", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper()
                    )
                    app_state.strategies["GammaScalper"] = strategy
                    strategy_registry["GammaScalper"] = strategy
            else:
                logger.warning("GammaScalper config not found, using default params")
                strategy = GammaScalper(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper()
                )
                app_state.strategies["GammaScalper"] = strategy
                strategy_registry["GammaScalper"] = strategy
        elif strategy_config.name == "CalendarArb":
            # Load T1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            t1_config_path = Path("configs/calendar_arb.yaml")
            if t1_config_path.exists():
                with open(t1_config_path, "r") as f:
                    t1_config = yaml.safe_load(f)
                    strategy = CalendarArb(
                        strategy_config.name,
                        t1_config.get("calendar_arb", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper()
                    )
                    app_state.strategies["CalendarArb"] = strategy
                    strategy_registry["CalendarArb"] = strategy
            else:
                logger.warning("CalendarArb config not found, using default params")
                strategy = CalendarArb(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper()
                )
                app_state.strategies["CalendarArb"] = strategy
                strategy_registry["CalendarArb"] = strategy
        elif strategy_config.name == "DispersionArb":
            # Load D1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            d1_config_path = Path("configs/dispersion_arb.yaml")
            if d1_config_path.exists():
                with open(d1_config_path, "r") as f:
                    d1_config = yaml.safe_load(f)
                    strategy = DispersionArb(
                        strategy_config.name,
                        d1_config.get("dispersion_arb", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper()
                    )
                    app_state.strategies["DispersionArb"] = strategy
                    strategy_registry["DispersionArb"] = strategy
            else:
                logger.warning("DispersionArb config not found, using default params")
                strategy = DispersionArb(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper()
                )
                app_state.strategies["DispersionArb"] = strategy
                strategy_registry["DispersionArb"] = strategy
        elif strategy_config.name == "TailShortVolOverlay":
            # Load H1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            h1_config_path = Path("configs/tail_short_vol.yaml")
            if h1_config_path.exists():
                with open(h1_config_path, "r") as f:
                    h1_config = yaml.safe_load(f)
                    strategy = TailShortVolOverlay(
                        strategy_config.name,
                        h1_config.get("tail_short_vol", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper(),
                        positions_store=app_state.position_store
                    )
                    app_state.strategies["TailShortVolOverlay"] = strategy
                    strategy_registry["TailShortVolOverlay"] = strategy
            else:
                logger.warning("TailShortVolOverlay config not found, using default params")
                strategy = TailShortVolOverlay(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper(),
                    positions_store=app_state.position_store
                )
                app_state.strategies["TailShortVolOverlay"] = strategy
                strategy_registry["TailShortVolOverlay"] = strategy
        elif strategy_config.name == "expiry_short_strangle_v2":
            # Load Expiry Short Strangle V2 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            
            v2_config_path = Path("configs/expiry_short_strangle_v2.yaml")
            if v2_config_path.exists():
                with open(v2_config_path, "r") as f:
                    v2_config = yaml.safe_load(f)
                    strategy = ExpiryShortStrangleV2(
                        strategy_config.name,
                        v2_config.get("expiry_short_strangle_v2", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper(),
                        regime_engine=app_state.strategies.get("RegimeVolEngine")
                    )
                    app_state.strategies["expiry_short_strangle_v2"] = strategy
                    strategy_registry["expiry_short_strangle_v2"] = strategy
                    logger.info("Strategy Loaded: Expiry Short Strangle V2")
            else:
                logger.warning("Expiry Short Strangle V2 config not found, using default params")
                strategy = ExpiryShortStrangleV2(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper(),
                    regime_engine=app_state.strategies.get("RegimeVolEngine")
                )
                app_state.strategies["expiry_short_strangle_v2"] = strategy
                strategy_registry["expiry_short_strangle_v2"] = strategy
        elif strategy_config.name == "intraday_short_strangle_v1":
            # Load Intraday Short Strangle V1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            from packages.core.options.delta_selector import DeltaOptionSelector
            from packages.core.kite_client import KiteClient
            
            # Create shared delta selector (if not already created)
            if not hasattr(app_state, 'delta_selector') or app_state.delta_selector is None:
                kite_client_wrapper = KiteClient(app_state.kite) if app_state.kite else None
                app_state.delta_selector = DeltaOptionSelector(
                    instrument_manager=app_state.instrument_manager,
                    broker_client=kite_client_wrapper or app_state.kite,
                    greeks_engine=None  # Optional - can be added later if available
                )
                logger.info("Shared DeltaOptionSelector created")
            
            # Create KiteClient wrapper for order placement
            kite_client_wrapper = KiteClient(app_state.kite) if app_state.kite else None
            
            v1_config_path = Path("configs/intraday_short_strangle_v1.yaml")
            if v1_config_path.exists():
                with open(v1_config_path, "r") as f:
                    v1_config = yaml.safe_load(f)
                    strategy = IntradayShortStrangleV1(
                        strategy_config.name,
                        v1_config.get("intraday_short_strangle_v1", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper(),
                        regime_engine=app_state.strategies.get("RegimeVolEngine"),
                        event_engine=app_state.strategies.get("EventVolEngine"),
                        delta_selector=app_state.delta_selector,
                        kite_client=kite_client_wrapper,
                        execution_engine=app_state.execution_engine,
                    )
                    app_state.strategies["intraday_short_strangle_v1"] = strategy
                    strategy_registry["intraday_short_strangle_v1"] = strategy
                    logger.info("Strategy Loaded: Intraday Short Strangle V1")
            else:
                logger.warning("Intraday Short Strangle V1 config not found, using default params")
                strategy = IntradayShortStrangleV1(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper(),
                        regime_engine=app_state.strategies.get("RegimeVolEngine"),
                        event_engine=app_state.strategies.get("EventVolEngine"),
                        delta_selector=app_state.delta_selector,
                        kite_client=kite_client_wrapper,
                        execution_engine=app_state.execution_engine,
                    )
                app_state.strategies["intraday_short_strangle_v1"] = strategy
                strategy_registry["intraday_short_strangle_v1"] = strategy
        elif strategy_config.name == "trend_credit_spread_v1":
            # Load Trend Credit Spread V1 config from separate YAML file
            import yaml
            from pathlib import Path
            from packages.core.metrics_wrapper import MetricsWrapper
            from packages.core.kite_client import KiteClient
            from packages.core.options.delta_selector import DeltaOptionSelector
            
            # Create shared delta selector (if not already created)
            if not hasattr(app_state, 'delta_selector') or app_state.delta_selector is None:
                kite_client_wrapper = KiteClient(app_state.kite) if app_state.kite else None
                app_state.delta_selector = DeltaOptionSelector(
                    instrument_manager=app_state.instrument_manager,
                    broker_client=kite_client_wrapper or app_state.kite,
                    greeks_engine=None  # Optional - can be added later if available
                )
                logger.info("Shared DeltaOptionSelector created")
            
            # Create KiteClient wrapper for order placement
            kite_client_wrapper = KiteClient(app_state.kite) if app_state.kite else None
            
            v1_config_path = Path("configs/trend_credit_spread_v1.yaml")
            if v1_config_path.exists():
                with open(v1_config_path, "r") as f:
                    v1_config = yaml.safe_load(f)
                    strategy = TrendCreditSpreadV1(
                        strategy_config.name,
                        v1_config.get("trend_credit_spread_v1", {}),
                        instrument_manager=app_state.instrument_manager,
                        risk_engine=app_state.risk_manager,
                        metrics=MetricsWrapper(),
                        kite_client=kite_client_wrapper,
                        position_store=app_state.position_store,
                        delta_selector=app_state.delta_selector,
                        regime_engine=app_state.strategies.get("RegimeVolEngine"),
                        event_engine=app_state.strategies.get("EventVolEngine"),
                        execution_engine=app_state.execution_engine,
                    )
                    app_state.strategies["trend_credit_spread_v1"] = strategy
                    strategy_registry["trend_credit_spread_v1"] = strategy
                    logger.info("Strategy Loaded: Trend Credit Spread V1")
            else:
                logger.warning("Trend Credit Spread V1 config not found, using default params")
                strategy = TrendCreditSpreadV1(
                    strategy_config.name,
                    strategy_config.params,
                    instrument_manager=app_state.instrument_manager,
                    risk_engine=app_state.risk_manager,
                    metrics=MetricsWrapper(),
                    kite_client=kite_client_wrapper,
                    position_store=app_state.position_store,
                    delta_selector=app_state.delta_selector,
                    regime_engine=app_state.strategies.get("RegimeVolEngine"),
                    event_engine=app_state.strategies.get("EventVolEngine"),
                    execution_engine=app_state.execution_engine,
                )
                app_state.strategies["trend_credit_spread_v1"] = strategy
                strategy_registry["trend_credit_spread_v1"] = strategy
        
        if strategy:
            # Patch 2: Set priority from config (default 100 if not specified)
            strategy_priority = getattr(strategy_config, 'priority', None)
            if strategy_priority is None:
                # Try to get from params
                strategy_priority = strategy_config.params.get('priority', 100)
            else:
                strategy_priority = int(strategy_priority)
            
            # Set priority on strategy instance
            strategy.priority = strategy_priority
            strategy_list.append(strategy)
            logger.debug(
                f"Strategy {strategy.name} loaded with priority {strategy.priority}",
                strategy=strategy.name,
                priority=strategy.priority
            )
    
    app_state.strategy_list = strategy_list
    
    # Log strategy priorities for verification
    strategy_priorities = [
        f"{s.name}(prio={getattr(s, 'priority', 100)})" 
        for s in strategy_list
    ]
    logger.info(
        f"Loaded {len(strategy_list)} strategies",
        strategies=", ".join(strategy_priorities)
    )
    
    # Initialize E1 Event Vol Engine
    import yaml
    from pathlib import Path
    from packages.core.event_vol_engine import EventVolEngine
    from packages.core.metrics_wrapper import MetricsWrapper
    
    event_cfg_path = Path("configs/event_vol_engine.yaml")
    if event_cfg_path.exists():
        with open(event_cfg_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        e1_cfg = raw.get("event_vol_engine", {})
        app_state.event_engine = EventVolEngine(cfg=e1_cfg, metrics=MetricsWrapper())
        logger.info("E1 Event Vol Engine initialized", enabled=e1_cfg.get("enabled", False))
    else:
        app_state.event_engine = EventVolEngine(cfg={"enabled": False}, metrics=None)
        logger.info("E1 Event Vol Engine disabled (config not found)")
    
    # Initialize StatsEngine (needed by StrategyAllocator)
    from packages.core.stats_engine import StatsEngine
    from packages.core.metrics_wrapper import MetricsWrapper
    
    stats_engine = StatsEngine(
        strategies=app_state.strategies,
        position_store=app_state.position_store
    )
    logger.info("StatsEngine initialized")
    
    # Initialize StrategyAllocator
    allocator_cfg_path = Path("configs/strategy_allocator.yaml")
    if allocator_cfg_path.exists():
        with open(allocator_cfg_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        allocator_cfg = raw.get("strategy_allocator", {})
        
        app_state.strategy_allocator = StrategyAllocator(
            cfg=allocator_cfg,
            risk_engine=app_state.risk_manager,
            stats_engine=stats_engine,
            metrics=MetricsWrapper()
        )
        logger.info(
            "StrategyAllocator initialized",
            enabled=allocator_cfg.get("enabled", False)
        )
        
        # Run initial allocation cycle if enabled
        if allocator_cfg.get("enabled", False):
            try:
                # For now, we can start with simple defaults
                current_regime = None
                event_ctx = None
                
                allocations = app_state.strategy_allocator.run_allocation_cycle(
                    current_regime=current_regime,
                    event_ctx=event_ctx
                )
                logger.info(
                    "Initial allocation cycle completed",
                    num_allocations=len(allocations)
                )
            except Exception as e:
                logger.warning(
                    "Allocation cycle failed at startup",
                    error=str(e)
                )
    else:
        logger.warning("StrategyAllocator config not found, allocator disabled")
        app_state.strategy_allocator = None
    
    # Initialize ranker
    app_state.ranker = SignalRanker(app_config.ranking)
    
    # Initialize and start market data stream
    app_state.market_data_stream.initialize()
    app_state.market_data_stream.start()
    
    # Subscribe to universe tokens after a short delay to allow connection
    async def subscribe_to_universe_delayed():
        await asyncio.sleep(3)  # Wait for WebSocket connection to establish
        if app_state.market_data_stream.is_connected:
            universe_tokens = app_state.instrument_manager.get_universe_tokens()
            if universe_tokens:
                # Subscribe to first 50 tokens (or all if less than 50)
                tokens_to_subscribe = universe_tokens[:50]
                app_state.market_data_stream.subscribe(tokens_to_subscribe)
                logger.info(f"Subscribed to {len(tokens_to_subscribe)} instruments for market data")
        else:
            logger.warning("Market data stream not connected, skipping subscription")
    
    # Start subscription task
    asyncio.create_task(subscribe_to_universe_delayed())
    
    # Initialize Redis bus
    redis_bus = RedisBus()
    await redis_bus.connect()
    logger.info("Redis bus connected")
    
    # Initialize Kite client wrapper (if needed)
    kite_client = KiteClient(app_state.kite)
    
    # Initialize OCO manager
    oco_manager = OCOManager(kite_client)
    logger.info("OCO manager initialized")
    
    # Initialize crypto router if in crypto mode
    app_state.crypto_router = None
    if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE"):
        from packages.core.venues.crypto_router import CryptoRouter
        from packages.core.models import Venue
        
        venue_config = getattr(app_config, "venue", {})
        venue_name = venue_config.get("name", "KRAKEN_SPOT")
        venue = Venue[venue_name] if venue_name in [v.name for v in Venue] else Venue.KRAKEN_SPOT
        
        # Get API credentials from environment
        secrets_env = venue_config.get("secrets_env", {})
        api_key = os.getenv(secrets_env.get("api_key", "KRAKEN_API_KEY"), "")
        api_secret = os.getenv(secrets_env.get("api_secret", "KRAKEN_API_SECRET"), "")
        
        if api_key and api_secret:
            # Choose exchange based on venue
            if venue == Venue.BINANCE_SPOT:
                from packages.exchanges.binance_spot import BinanceSpot
                # Use testnet if: CRYPTO_PAPER mode OR BINANCE_TESTNET env var is set
                use_testnet = (settings.app_mode.value == "CRYPTO_PAPER") or (os.getenv("BINANCE_TESTNET") == "1")
                exchange = BinanceSpot(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
            else:
                from packages.exchanges.kraken_spot import KrakenSpot
                exchange = KrakenSpot(api_key=api_key, api_secret=api_secret, testnet=(settings.app_mode.value == "CRYPTO_PAPER"))
            
            paper_mode = (settings.app_mode.value == "CRYPTO_PAPER")
            app_state.crypto_router = CryptoRouter(exchange=exchange, config=app_config, venue=venue, paper_mode=paper_mode)
            await app_state.crypto_router.initialize()
            logger.info("Crypto router initialized", venue=venue.value, paper_mode=paper_mode)
        else:
            logger.warning("Crypto API credentials not found, crypto router not initialized")
    
    # Initialize Delta Neutralizer (Phase-1 Safety Version)
    delta_neutralizer = None
    # Load delta_neutralizer config from YAML (it's not in AppConfig class yet)
    import yaml
    from pathlib import Path
    config_path = Path(app_config.config_path) if hasattr(app_config, 'config_path') else Path("configs/kite_day1_live.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)
            dn_cfg_raw = raw_config.get("delta_neutralizer", {})
            
            if dn_cfg_raw:
                dn_cfg = DeltaNeutralizerConfig(
                    enabled=dn_cfg_raw.get("enabled", True),
                    underlying=dn_cfg_raw.get("underlying", "NIFTY"),
                    fut_symbol=dn_cfg_raw.get("fut_symbol", "NFO:NIFTY24NOVFUT"),
                    rebalance_threshold=float(dn_cfg_raw.get("rebalance_threshold", 50.0)),
                    max_hedge_lots=int(dn_cfg_raw.get("max_hedge_lots", 2)),
                    lot_size=int(dn_cfg_raw.get("lot_size", 25)),
                )
                
                delta_neutralizer = DeltaNeutralizer(
                    kite_client=app_state.kite,
                    position_store=app_state.position_store,
                    cfg=dn_cfg,
                )
                logger.info("Delta Neutralizer initialized", enabled=dn_cfg.enabled)
            else:
                logger.info("Delta Neutralizer config not found in YAML, skipping initialization")
    else:
        logger.warning(f"Config file not found: {config_path}, skipping Delta Neutralizer initialization")
    
    # Initialize orchestrator with Redis and OCO
    app_state.orchestrator = TradingOrchestrator(
        kite=app_state.kite,
        strategies=strategy_list,
        instrument_manager=app_state.instrument_manager,
        market_data_stream=app_state.market_data_stream,
        risk_manager=app_state.risk_manager,
        execution_engine=app_state.execution_engine,
        exit_manager=app_state.exit_manager,
        ranker=app_state.ranker,
        position_store=app_state.position_store,
        redis_bus=redis_bus,
        strategy_allocator=app_state.strategy_allocator,
        oco_manager=oco_manager,
        crypto_router=app_state.crypto_router,
        delta_neutralizer=delta_neutralizer
    )
    
    # Initialize OrderWatcher
    order_watcher = OrderWatcher(
        kite_client=kite_client,
        orchestrator=app_state.orchestrator,
        oco_manager=oco_manager,
        redis_bus=redis_bus,
        metrics=None  # Can pass metrics if needed
    )
    
    # Start heartbeat updater
    from packages.core.heartbeats import run_heartbeat_updater
    hb_stop = asyncio.Event()
    hb_task = asyncio.create_task(run_heartbeat_updater(1.0, hb_stop))
    app_state.hb_stop = hb_stop
    app_state.hb_task = hb_task
    logger.info("Heartbeat updater started")
    
    # Start paper tick simulator if in PAPER mode and market data not connected
    if settings.app_mode.value == "PAPER" and not app_state.market_data_stream.is_connected:
        async def run_paper_tick_simulator():
            """Simulate market data ticks in PAPER mode"""
            from packages.core.heartbeats import touch_marketdata
            while not hb_stop.is_set():
                touch_marketdata()
                await asyncio.sleep(0.5)  # Simulate tick every 500ms
        
        paper_tick_task = asyncio.create_task(run_paper_tick_simulator())
        app_state.paper_tick_task = paper_tick_task
        logger.info("Paper tick simulator started")
    
    # Start pre-live metrics refresh task (every 30s)
    async def refresh_prelive_metrics_task():
        """Periodic task to refresh pre-live gate metrics"""
        from pathlib import Path
        import time
        import json
        from packages.core.metrics import prelive_day2_pass, prelive_day2_age
        
        DAY2_DIR = Path("reports/burnin")
        FRESH_SECS = 36 * 3600
        
        def _latest_day2_json():
            files = sorted(DAY2_DIR.glob("day2_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            return files[0] if files else None
        
        while not hb_stop.is_set():
            try:
                p = _latest_day2_json()
                if not p:
                    prelive_day2_pass.set(0)
                    prelive_day2_age.set(float("inf"))
                else:
                    age = time.time() - p.stat().st_mtime
                    prelive_day2_age.set(age)
                    try:
                        with p.open() as f:
                            data = json.load(f)
                        if (data.get("status") == "PASS" and 
                            int(data.get("leader", 0)) == 1 and
                            age <= FRESH_SECS):
                            prelive_day2_pass.set(1)
                        else:
                            prelive_day2_pass.set(0)
                    except Exception:
                        prelive_day2_pass.set(0)
            except Exception as e:
                logger.warning(f"Error refreshing pre-live metrics: {e}")
            await asyncio.sleep(30)  # Refresh every 30s
    
    prelive_metrics_task = asyncio.create_task(refresh_prelive_metrics_task())
    app_state.prelive_metrics_task = prelive_metrics_task
    logger.info("Pre-live metrics refresh task started")
    
    # Start background tasks
    logger.info("Starting background tasks...")
    tasks = [
        asyncio.create_task(app_state.orchestrator.start()),
        asyncio.create_task(order_watcher.start())
    ]
    app_state.tasks = tasks
    
    logger.info("AITRAPP started successfully")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down AITRAPP")
    
    # Stop heartbeat updater
    if hasattr(app_state, 'hb_stop') and app_state.hb_stop:
        app_state.hb_stop.set()
    if hasattr(app_state, 'hb_task') and app_state.hb_task:
        try:
            await app_state.hb_task
        except Exception as e:
            logger.warning(f"Error stopping heartbeat updater: {e}")
    
    # Stop pre-live metrics refresh task
    if hasattr(app_state, 'prelive_metrics_task') and app_state.prelive_metrics_task:
        try:
            app_state.prelive_metrics_task.cancel()
            await app_state.prelive_metrics_task
        except Exception as e:
            logger.warning(f"Error stopping pre-live metrics task: {e}")
    
    # Stop paper tick simulator
    if hasattr(app_state, 'paper_tick_task') and app_state.paper_tick_task:
        try:
            app_state.paper_tick_task.cancel()
            await app_state.paper_tick_task
        except Exception as e:
            logger.warning(f"Error stopping paper tick simulator: {e}")
    
    # Pause orchestrator
    if app_state.orchestrator:
        await app_state.orchestrator.pause()
        try:
            await app_state.orchestrator.flatten_all()
        except Exception as e:
            logger.error("Error during flatten", error=str(e))
    
    # Stop OrderWatcher
    if order_watcher:
        order_watcher.stop()
    
    # Cancel all tasks
    for task in tasks:
        task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Disconnect Redis
    if redis_bus:
        await redis_bus.disconnect()
    
    # Stop market data stream
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
# Note: In production, set exact origins: allow_origins=["https://ops-ui.yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.20.10.4:3000",  # Network IP for Ops Browser
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only methods we actually use
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Ops-Key"],  # Headers we send
    expose_headers=["X-Retry-After", "X-Rate-Limit-Remaining", "X-Time-Skew-Ms"],  # Headers UI reads
    max_age=600,  # Cache preflight for 10 minutes
)

# Exception handler to ensure CORS headers on errors
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Ensure CORS headers are included even on unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    origin = request.headers.get("origin", "*")
    # Use exact origin if it's in allowed list, otherwise use the origin from request
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if origin not in allowed_origins and origin != "*":
        origin = "*"  # Fallback to wildcard for unknown origins in dev
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": str(exc), "ready": False},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Ops-Key, X-Request-ID",
            "Access-Control-Expose-Headers": "X-Retry-After, X-Rate-Limit-Remaining, X-Time-Skew-Ms",
            "Vary": "Origin",
        }
    )

# Mount Prometheus metrics
if settings.enable_metrics:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Include debug routers
from apps.api import debug, debug_supervisor
app.include_router(debug.router, tags=["debug"])
app.include_router(debug_supervisor.router, tags=["debug"])

# Include MCP analyst router
from apps.api.routes import mcp_analyst
app.include_router(mcp_analyst.router, tags=["mcp-analyst"])


# ===== API Models =====

class ModeChangeRequest(BaseModel):
    mode: str  # PAPER or LIVE
    confirmation: str = ""
    override_reason: Optional[str] = None  # Required for manual override


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
    marketdata_connected: Optional[bool] = None
    websocket_connected: Optional[bool] = None
    subscription_count: Optional[int] = None


# ===== Control Endpoints =====

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_data = {
        "status": "healthy",
        "mode": settings.app_mode.value,
        "is_paused": app_state.is_paused,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add crypto venue info if in crypto mode
    if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE"):
        venue_config = getattr(app_config, "venue", {})
        if venue_config:
            health_data["crypto_venue"] = venue_config.get("name", "UNKNOWN")
            health_data["allowed_symbols"] = venue_config.get("allowed_symbols", [])
            health_data["maker_fee_bps"] = venue_config.get("maker_fee_bps", 0)
            health_data["taker_fee_bps"] = venue_config.get("taker_fee_bps", 0)
            
            # Add precision info for top 3 symbols (if crypto router initialized)
            # Note: This is optional and may not be available on first health check
            try:
                if hasattr(app_state, "crypto_router") and app_state.crypto_router:
                    symbols = venue_config.get("allowed_symbols", [])[:3]
                    precision_info = {}
                    for sym in symbols:
                        symbol_info = await app_state.crypto_router.exchange.get_symbol_info(sym)
                        if symbol_info:
                            precision_info[sym] = {
                                "tick_size": float(symbol_info.tick_size),
                                "step_size": float(symbol_info.step_size),
                                "min_notional": float(symbol_info.min_notional)
                            }
                    if precision_info:
                        health_data["precision"] = precision_info
            except Exception as e:
                # Silently fail - precision info is optional
                pass
    
    # Return JSONResponse to ensure CORS expose headers are included
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=health_data,
        headers={
            "Access-Control-Expose-Headers": "X-Retry-After, X-Rate-Limit-Remaining, X-Time-Skew-Ms",
            "Vary": "Origin",
        }
    )


@app.get("/ready", response_class=JSONResponse)
async def ready():
    """Readiness endpoint - returns 200 only when leader lock is held and all heartbeats are fresh"""
    import os
    from packages.core.metrics import (
        is_leader,
        marketdata_heartbeat_seconds,
        order_stream_heartbeat_seconds,
        scan_heartbeat_seconds,
    )
    
    HEARTBEAT_MAX = float(os.getenv("HEARTBEAT_MAX", "5"))
    
    # Prometheus client stores values on samples()[0].value
    def get_value(gauge):
        """Get current value from Prometheus gauge"""
        samples = list(gauge._samples())
        if samples:
            return samples[0].value
        return 999.0  # Default to stale if no samples
    
    try:
        leader_val = get_value(is_leader)
        md_heartbeat = get_value(marketdata_heartbeat_seconds)
        order_heartbeat = get_value(order_stream_heartbeat_seconds)
        scan_heartbeat = get_value(scan_heartbeat_seconds)
        
        ok = (
            leader_val == 1
            and md_heartbeat < HEARTBEAT_MAX
            and order_heartbeat < HEARTBEAT_MAX
            and scan_heartbeat < HEARTBEAT_MAX
        )
        
        if not ok:
            # Return JSONResponse with CORS headers instead of raising HTTPException
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "ready": False,
                    "status": "not_ready",
                    "mode": settings.app_mode.value,
                    "leader": int(leader_val),
                    "marketdata_heartbeat": md_heartbeat,
                    "order_stream_heartbeat": order_heartbeat,
                    "scan_heartbeat": scan_heartbeat,
                    "heartbeat_max": HEARTBEAT_MAX
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Ops-Key, X-Request-ID",
                    "Access-Control-Expose-Headers": "X-Retry-After, X-Rate-Limit-Remaining, X-Time-Skew-Ms",
                    "Vary": "Origin",
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                }
            )
        
        response = JSONResponse(
            content={
                "ok": True,
                "ready": True,
                "status": "ready",
                "mode": settings.app_mode.value,
                "leader": int(leader_val),
                "marketdata_heartbeat": md_heartbeat,
                "order_stream_heartbeat": order_heartbeat,
                "scan_heartbeat": scan_heartbeat
            },
            headers={
                "Vary": "Origin",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
        return response
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        # Return JSONResponse with CORS headers instead of raising HTTPException
        # This ensures CORS headers are present even on errors
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "ready": False,
                "status": "not_ready",
                "mode": settings.app_mode.value if hasattr(settings, 'app_mode') else "UNKNOWN",
                "error": str(e)
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Ops-Key, X-Request-ID",
                "Access-Control-Expose-Headers": "X-Retry-After, X-Rate-Limit-Remaining, X-Time-Skew-Ms",
                "Vary": "Origin",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )


@app.get("/compliance/status")
def compliance_status():
    """SEBI/NSE compliance status endpoint"""
    expected_ip = os.getenv("EXPECTED_EGRESS_IP", "")
    algo_id = os.getenv("EXCHANGE_ALGO_ID", "").strip()
    tops_cap = int(os.getenv("TOPS_CAP_PER_SEC", "8"))
    mode_profile = os.getenv("MODE_PROFILE", "PERSONAL").upper()
    wl = os.getenv("WHITELISTED_CLIENTS", "")
    # broker session created_at iso if you persist it, else env fallback:
    oauth_created_iso = os.getenv("KITE_TOKEN_CREATED_AT_ISO")
    # active client ids: if you have multiple mapped, load from your config/session
    active_clients = [app_state.get("kite_user_id")] if app_state.get("kite_user_id") else []
    if settings.kite_user_id:
        active_clients = list(set(active_clients + [settings.kite_user_id]))
    
    ip_ok, ip_msg, curr_ip = compliance.check_static_ip(expected_ip)
    oauth_ok, oauth_msg = compliance.check_oauth_fresh(oauth_created_iso, 24)
    tops_ok, tops_msg = compliance.tops_cap_ok(tops_cap)
    algo_ok, algo_msg = compliance.algo_id_present(algo_id)
    fam_ok, fam_msg = (True, "provider mode") if mode_profile != "PERSONAL" else compliance.check_family_only(active_clients, wl)
    
    return {
        "mode": os.getenv("APP_MODE", "PAPER"),
        "profile": mode_profile,
        "expected_ip": expected_ip,
        "current_ip": curr_ip,
        "static_ip_ok": ip_ok,
        "static_ip_msg": ip_msg,
        "oauth_ok": oauth_ok,
        "oauth_msg": oauth_msg,
        "tops_ok": tops_ok,
        "tops_msg": tops_msg,
        "tops_cap_per_sec": tops_cap,
        "algo_id_ok": algo_ok,
        "algo_msg": algo_msg,
        "exchange_algo_id": algo_id,
        "family_ok": fam_ok,
        "family_msg": fam_msg,
    }


@app.post("/mode")
async def change_mode(request: ModeChangeRequest):
    """
    Change application mode (PAPER <-> LIVE).
    
    LIVE mode requires explicit confirmation and validates Day-2 scorer JSON.
    For manual override, provide override_reason (logged to AuditLog).
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
        
        # Gate on scorer JSON: require Day-2 PASS before LIVE switch
        # Mirrors the shell gate logic (mtime-based selection, freshness, completeness)
        import os
        import json
        import subprocess
        import time
        from pathlib import Path
        from datetime import datetime, timedelta
        
        DAY2_DIR = Path("reports/burnin")
        FRESH_SECS = 36 * 3600  # 36 hours
        
        def _latest_day2_json() -> Path | None:
            """Select latest Day-2 JSON by mtime (not filename)"""
            files = sorted(DAY2_DIR.glob("day2_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            return files[0] if files else None
        
        def _validate_day2_json_or_403():
            """Validate Day-2 JSON with same logic as shell gate"""
            p = _latest_day2_json()
            if not p:
                raise HTTPException(status_code=403, detail="Day-2 JSON missing")
            
            age = time.time() - p.stat().st_mtime
            if age > FRESH_SECS:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON stale (age={int(age/3600)}h, max 36h)")
            
            with p.open() as f:
                data = json.load(f)
            
            # Required fields
            req = ["status", "leader", "heartbeats", "leader_changes", "duplicates", "orphans", "flatten_ms"]
            if any(k not in data for k in req):
                raise HTTPException(status_code=403, detail="Day-2 JSON incomplete")
            
            # Validate heartbeats structure
            if "heartbeats" not in data or not isinstance(data["heartbeats"], dict):
                raise HTTPException(status_code=403, detail="Day-2 JSON: heartbeats missing or invalid")
            
            hb = data["heartbeats"]
            hb_keys = ["market", "orders", "scan"]
            if any(k not in hb for k in hb_keys):
                raise HTTPException(status_code=403, detail="Day-2 JSON: heartbeat keys missing")
            
            # Hard checks (fail closed)
            if data.get("status") != "PASS":
                raise HTTPException(status_code=403, detail=f"Day-2 JSON status={data.get('status')} (expected PASS)")
            
            if int(data.get("leader", 0)) != 1:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON leader={data.get('leader')} (expected 1)")
            
            if any(float(hb.get(k, 999)) >= 5 for k in hb_keys):
                raise HTTPException(status_code=403, detail=f"Day-2 JSON: heartbeats >= 5s (market={hb.get('market')}, orders={hb.get('orders')}, scan={hb.get('scan')})")
            
            if int(data.get("leader_changes", 999)) > 2:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON: leader_changes={data.get('leader_changes')} (>2)")
            
            if int(data.get("duplicates", 999)) != 0:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON: duplicates={data.get('duplicates')} (!=0)")
            
            if int(data.get("orphans", 999)) != 0:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON: orphans={data.get('orphans')} (!=0)")
            
            if float(data.get("flatten_ms", 9999)) > 2000:
                raise HTTPException(status_code=403, detail=f"Day-2 JSON: flatten_ms={data.get('flatten_ms')}ms (>2000ms)")
        
        # Find latest Day-2 JSON by mtime (not filename)
        day2_json = _latest_day2_json()
        
        if day2_json and day2_json.exists():
            try:
                # Use the same validation logic as shell gate
                _validate_day2_json_or_403()
                
                # Additional: Validate config_sha and git_head match runtime
                with open(day2_json) as f:
                    day2_data = json.load(f)
                
                runtime_config_sha = None
                runtime_git_head = None
                
                try:
                    import hashlib
                    with open("configs/app.yaml", "rb") as f:
                        runtime_config_sha = hashlib.sha256(f.read()).hexdigest()[:16]
                except Exception:
                    pass
                
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "--short", "HEAD"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        runtime_git_head = result.stdout.strip()
                except Exception:
                    pass
                
                json_config_sha = day2_data.get("config_sha")
                json_git_head = day2_data.get("git_head")
                
                if runtime_config_sha and json_config_sha and runtime_config_sha != json_config_sha:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Config SHA mismatch (JSON={json_config_sha}, runtime={runtime_config_sha}). Config changed after Day-2 PASS. Cannot switch to LIVE."
                    )
                
                if runtime_git_head and json_git_head and runtime_git_head != json_git_head:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Git HEAD mismatch (JSON={json_git_head}, runtime={runtime_git_head}). Code changed after Day-2 PASS. Cannot switch to LIVE."
                    )
                
                logger.info("Day-2 scorer JSON check passed with full validation", json_file=str(day2_json))
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Could not validate Day-2 scorer JSON: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error validating Day-2 scorer JSON: {str(e)}"
                )
        else:
            logger.warning("No Day-2 scorer JSON found - proceeding with caution")
            # Don't block, but warn
        
        # Mode safety: assert APP_MODE isn't already LIVE
        if settings.app_mode.value == "LIVE":
            raise HTTPException(
                status_code=400,
                detail="Already in LIVE mode. No need to switch again."
            )
        
        # Log config_sha + git_head to AuditLog before flip (hardens audit trail)
        try:
            from packages.storage.persistence import get_db_session
            from packages.storage.models import AuditLog, AuditActionEnum
            import hashlib
            import subprocess
            
            runtime_config_sha = None
            runtime_git_head = None
            
            try:
                with open("configs/app.yaml", "rb") as f:
                    runtime_config_sha = hashlib.sha256(f.read()).hexdigest()[:16]
            except Exception:
                pass
            
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    runtime_git_head = result.stdout.strip()
            except Exception:
                pass
            
            async with get_db_session() as session:
                audit_log = AuditLog(
                    action=AuditActionEnum.MODE_CHANGE,
                    details={
                        "mode": "LIVE",
                        "config_sha": runtime_config_sha or "unknown",
                        "git_head": runtime_git_head or "unknown",
                        "timestamp": datetime.now().isoformat(),
                        "day2_json_validated": day2_json is not None
                    }
                )
                session.add(audit_log)
                await session.commit()
                logger.info("Mode change logged to AuditLog", config_sha=runtime_config_sha, git_head=runtime_git_head)
        except Exception as e:
            logger.warning(f"Could not log mode change to AuditLog: {e}")
            # Don't block mode change if audit logging fails
        
        # Manual override check
        override_reason = getattr(request, "override_reason", None)
        if override_reason:
            # Log override to AuditLog
            from packages.storage.persistence import get_db_session
            from packages.storage.models import AuditLog, AuditActionEnum
            try:
                async with get_db_session() as session:
                    audit_log = AuditLog(
                        action=AuditActionEnum.MODE_CHANGE,
                        details={
                            "mode": "LIVE",
                            "override": True,
                            "override_reason": override_reason,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    session.add(audit_log)
                    await session.commit()
            except Exception as e:
                logger.warning(f"Could not log override to AuditLog: {e}")
            
            # Create incident snapshot before flipping
            try:
                import subprocess
                snapshot_dir = Path("reports/incidents")
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                snapshot_file = snapshot_dir / f"override_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(snapshot_file, "w") as f:
                    f.write(f"LIVE Mode Override Snapshot\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Override Reason: {override_reason}\n")
                    f.write(f"Git HEAD: {subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()}\n")
                    f.write(f"Config SHA: {runtime_config_sha if 'runtime_config_sha' in locals() else 'unknown'}\n")
                    f.write(f"Positions: {len(app_state.positions)}\n")
                    f.write(f"Paused: {app_state.is_paused}\n")
                logger.warning(f"Incident snapshot created: {snapshot_file}")
            except Exception as e:
                logger.warning(f"Could not create incident snapshot: {e}")
        
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
    if app_state.orchestrator:
        await app_state.orchestrator.pause()
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
    if app_state.orchestrator:
        await app_state.orchestrator.resume()
        app_state.is_paused = False
    
    logger.info("▶️  TRADING RESUMED")
    
    return {
        "status": "resumed",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/market-data/restart")
async def restart_market_data():
    """Restart market data WebSocket connection"""
    try:
        if app_state.market_data_stream:
            logger.info("Restarting market data WebSocket connection")
            
            # Reload token from .env file
            from dotenv import load_dotenv
            import os
            load_dotenv()
            new_token = os.getenv("KITE_ACCESS_TOKEN")
            if new_token:
                # Update settings with new token
                settings.kite_access_token = new_token
                # Also update KiteConnect instance
                app_state.kite.set_access_token(new_token)
                logger.info("Token reloaded from .env file")
            
            # Stop existing connection
            app_state.market_data_stream.stop()
            await asyncio.sleep(2)  # Give it time to fully stop
            
            # Reinitialize with fresh token
            app_state.market_data_stream.initialize()
            app_state.market_data_stream.start()
            
            # Wait longer for connection (WebSocket can take 5-10 seconds)
            max_wait = 20  # Increased to 20 seconds
            waited = 0
            while not app_state.market_data_stream.is_connected and waited < max_wait:
                await asyncio.sleep(1)
                waited += 1
                if waited % 5 == 0:  # Log every 5 seconds
                    logger.info(f"Waiting for WebSocket connection... ({waited}/{max_wait}s)")
            
            if not app_state.market_data_stream.is_connected:
                logger.warning(
                    f"WebSocket not connected after {waited} seconds. "
                    "This may indicate a token issue or WebSocket streaming not enabled in Kite app settings."
                )
            
            # Resubscribe to universe if connected
            if app_state.market_data_stream.is_connected:
                if app_state.orchestrator:
                    universe_tokens = app_state.instrument_manager.get_universe_tokens()
                    if universe_tokens:
                        app_state.market_data_stream.subscribe(universe_tokens[:50])
                        logger.info(f"Resubscribed to {len(universe_tokens[:50])} instruments")
            
            return {
                "status": "success",
                "message": "Market data WebSocket restarted",
                "connected": app_state.market_data_stream.is_connected,
                "waited_seconds": waited,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Market data stream not initialized")
    except Exception as e:
        logger.error(f"Failed to restart market data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flatten")
async def flatten_all(reason: str = "manual"):
    """
    Flatten (close) all positions.
    
    For crypto mode, uses crypto router to flatten positions.
    For equity mode, uses orchestrator flatten_all.
    """
    import time
    from packages.core.metrics import crypto_flatten_duration_seconds
    
    start_time = time.time()
    
    if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE") and app_state.crypto_router:
        # Use crypto router to flatten
        orders = await app_state.crypto_router.flatten()
        
        # Record duration metric
        duration = time.time() - start_time
        venue = getattr(app_state.crypto_router, 'venue', None)
        if venue:
            crypto_flatten_duration_seconds.labels(venue=venue.value).observe(duration)
        
        return {
            "status": "flattened",
            "reason": reason,
            "orders": len(orders),
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now().isoformat()
        }
    
    # Equity mode - use orchestrator
    if app_state.orchestrator:
        await app_state.orchestrator.flatten_all(reason=reason)
        duration = time.time() - start_time
        return {
            "status": "flattened",
            "reason": reason,
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "status": "no_positions",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }


# ===== Data Endpoints =====

@app.get("/positions")
async def get_positions():
    """Get all open positions"""
    positions_list = app_state.orchestrator.positions if app_state.orchestrator else app_state.positions
    
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
        for pos in positions_list if pos.is_open
    ]
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={
            "positions": positions,
            "count": len(positions)
        },
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


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
    try:
        # Get market data connection status
        marketdata_connected = None
        websocket_connected = None
        subscription_count = None
        
        if app_state.market_data_stream:
            marketdata_connected = app_state.market_data_stream.is_connected
            websocket_connected = app_state.market_data_stream.is_connected
            subscription_count = len(app_state.market_data_stream.subscribed_tokens) if hasattr(app_state.market_data_stream, 'subscribed_tokens') else None
        
        if app_state.orchestrator:
            system_state = app_state.orchestrator.get_system_state()
            return SystemStateResponse(
                timestamp=system_state.timestamp.isoformat(),
                mode=system_state.mode,
                is_paused=system_state.is_paused,
                is_market_open=system_state.is_market_open,
                positions_count=system_state.portfolio.total_positions,
                trades_today=system_state.trades_today,
                win_rate=system_state.win_rate,
                daily_pnl=system_state.portfolio.daily_pnl,
                marketdata_connected=marketdata_connected,
                websocket_connected=websocket_connected,
                subscription_count=subscription_count
            )
        else:
            # Fallback if orchestrator not initialized
            win_rate = 0.0
            if app_state.trades_today > 0:
                win_rate = (app_state.wins_today / app_state.trades_today) * 100
            
            # Get market data connection status
            marketdata_connected = None
            websocket_connected = None
            subscription_count = None
            
            if app_state.market_data_stream:
                marketdata_connected = app_state.market_data_stream.is_connected
                websocket_connected = app_state.market_data_stream.is_connected
                subscription_count = len(app_state.market_data_stream.subscribed_tokens) if hasattr(app_state.market_data_stream, 'subscribed_tokens') else None
            
            return SystemStateResponse(
                timestamp=datetime.now().isoformat(),
                mode=settings.app_mode.value,
                is_paused=app_state.is_paused,
                is_market_open=app_state.is_market_open,
                positions_count=len([p for p in app_state.positions if p.is_open]),
                trades_today=app_state.trades_today,
                win_rate=win_rate,
                daily_pnl=app_state.realized_pnl_today,
                marketdata_connected=marketdata_connected,
                websocket_connected=websocket_connected,
                subscription_count=subscription_count
            )
    except Exception as e:
        logger.error(f"Error getting system state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/orders")
async def get_orders():
    """Get all orders"""
    orders = app_state.execution_engine.orders.values()
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={
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
        },
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


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


@app.get("/api/execution/stats")
async def get_execution_stats():
    """Get execution alpha telemetry stats"""
    try:
        if app_state.execution_engine:
            stats = app_state.execution_engine.get_limit_chase_stats()
            return stats
        return {}
    except Exception as e:
        logger.error(f"Error fetching execution stats: {e}", exc_info=True)
        return {}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint with cache control"""
    from packages.core.metrics import get_metrics
    return Response(
        content=get_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@app.get("/risk")
async def get_risk_state():
    """Get current risk state"""
    try:
        if not app_state.orchestrator or not app_state.risk_manager:
            raise HTTPException(status_code=503, detail="Risk manager not initialized")
        
        # Get portfolio risk
        portfolio_risk = app_state.orchestrator._get_portfolio_risk()
        
        return {
            "net_liquid": portfolio_risk.net_liquid,
            "used_margin": portfolio_risk.used_margin,
            "available_margin": portfolio_risk.available_margin,
            "total_risk_amount": portfolio_risk.total_risk_amount,
            "portfolio_heat_pct": portfolio_risk.portfolio_heat_pct,
            "unrealized_pnl": portfolio_risk.unrealized_pnl,
            "realized_pnl_today": portfolio_risk.realized_pnl_today,
            "daily_pnl": portfolio_risk.daily_pnl,
            "daily_pnl_pct": portfolio_risk.daily_pnl_pct,
            "daily_loss_limit": portfolio_risk.daily_loss_limit,
            "max_portfolio_heat": portfolio_risk.max_portfolio_heat,
            "is_daily_loss_breached": portfolio_risk.is_daily_loss_breached,
            "is_heat_limit_breached": portfolio_risk.is_heat_limit_breached,
            "can_take_new_position": portfolio_risk.can_take_new_position,
            "open_positions_count": len(portfolio_risk.open_positions),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
