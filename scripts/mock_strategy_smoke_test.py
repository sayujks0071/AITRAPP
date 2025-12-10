#!/usr/bin/env python3
"""
Mock smoke-test for enabled strategies.

Purpose
-------
Run each enabled strategy against synthetic market data to ensure
`generate_signals` executes without exceptions before paper/live runs.

Usage
-----
  APP_CONFIG=configs/app.yaml python3 scripts/mock_strategy_smoke_test.py
"""
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple, Type

from packages.core.config import app_config
from packages.core.models import (
    Instrument,
    InstrumentType,
    Bar,
    Tick,
)
from packages.core.strategies import (
    BollingerBandsStrategy,
    BreakoutStrategy,
    MACDStrategy,
    OptionsRankerStrategy,
    ORBStrategy,
    RSIMeanReversionStrategy,
    SMAMomentumStrategy,
    TrendPullbackStrategy,
)
from packages.core.strategies.base import Strategy, StrategyContext


@dataclass
class StrategyCase:
    cls: Type[Strategy]
    context_builder: Callable[[], StrategyContext]


def _base_instrument() -> Instrument:
    """Create a generic NIFTY future instrument."""
    return Instrument(
        token=12345,
        symbol="NIFTY",
        tradingsymbol="NIFTY24JULFUT",
        exchange="NSE",
        instrument_type=InstrumentType.FUT,
        lot_size=50,
        tick_size=0.05,
    )


def _build_bars(
    length: int,
    start_price: float,
    drift: float,
    rsi_value: Optional[float] = None,
    price_below_bb: bool = False,
) -> List[Bar]:
    """
    Build synthetic bars with indicators filled for strategy filters.
    
    Args:
        length: Number of bars to generate
        start_price: Starting close price
        drift: Price change per bar (positive = uptrend, negative = downtrend)
        rsi_value: Optional RSI value to set on the last bar
        price_below_bb: If True, set last price below lower band for mean reversion
    """
    bars: List[Bar] = []
    now = datetime.utcnow()
    price = start_price
    for i in range(length):
        price = max(1.0, price + drift)
        ts = now - timedelta(minutes=(length - i))
        bar = Bar(
            token=12345,
            timestamp=ts,
            open=price - 0.5,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=1_000_000 + i * 5_000,
        )
        bars.append(bar)
    
    # Fill indicators on the last two bars to satisfy crossover logic
    prev = bars[-2]
    curr = bars[-1]
    
    # MACD crossover bullish: prev below, current above
    prev.macd = -0.5
    prev.macd_signal = 0.0
    curr.macd = 1.0
    curr.macd_signal = 0.0
    
    # EMA & Supertrend for directional bias (OptionsRanker + others)
    prev.ema_fast = prev.close * 0.999
    prev.ema_slow = prev.close * 1.001
    prev.supertrend_direction = 1
    curr.ema_fast = curr.close * 1.002
    curr.ema_slow = curr.close * 0.998
    curr.supertrend_direction = 1
    
    # Bollinger Bands: place current price near lower band if requested
    curr.bb_middle = curr.close
    curr.bb_upper = curr.close * 1.02
    curr.bb_lower = curr.close * (0.98 if not price_below_bb else 0.995)
    if price_below_bb:
        curr.close = curr.bb_lower * 0.999  # force price slightly below lower band
    
    # RSI for mean reversion filters
    if rsi_value is not None:
        curr.rsi = rsi_value
    else:
        curr.rsi = 55.0
    
    return bars


def _make_context(
    *,
    mode: str,
    ivp: float = 40.0,
) -> StrategyContext:
    """Create a StrategyContext tuned for different test scenarios."""
    instrument = _base_instrument()
    if mode == "mean_reversion":
        bars_5s = _build_bars(length=60, start_price=19500, drift=-5.0, rsi_value=20.0, price_below_bb=True)
    elif mode == "breakout":
        bars_5s = _build_bars(length=60, start_price=19500, drift=5.0, rsi_value=60.0, price_below_bb=False)
        # Push last closes above prior highs to trigger breakout confirmation
        for bump in range(3):
            bars_5s[-(bump + 1)].close = bars_5s[-(bump + 1)].close * 1.01
            bars_5s[-(bump + 1)].high = bars_5s[-(bump + 1)].close * 1.002
    else:  # bullish / momentum
        bars_5s = _build_bars(length=60, start_price=19500, drift=3.0, rsi_value=60.0, price_below_bb=False)
    
    latest_tick = Tick(
        token=instrument.token,
        timestamp=datetime.utcnow(),
        last_price=bars_5s[-1].close,
        bid=bars_5s[-1].close - 0.1,
        ask=bars_5s[-1].close + 0.1,
        volume=bars_5s[-1].volume,
    )
    
    return StrategyContext(
        timestamp=datetime.utcnow(),
        instrument=instrument,
        latest_tick=latest_tick,
        bars_1s=bars_5s[-20:],  # reuse subset for 1s bars
        bars_5s=bars_5s,
        net_liquid=1_000_000,
        available_margin=500_000,
        open_positions=0,
        iv_percentile=ivp,
        backtest_mode=True,  # relaxed volume/R:R filters for smoke testing
        universe_size=1,
        token_count=1,
    )


def _strategy_cases() -> Dict[str, StrategyCase]:
    """Map strategy names to constructors + context builders."""
    return {
        "OptionsRanker": StrategyCase(OptionsRankerStrategy, lambda: _make_context(mode="bullish", ivp=40.0)),
        "SMAMomentum": StrategyCase(SMAMomentumStrategy, lambda: _make_context(mode="bullish")),
        "MACD": StrategyCase(MACDStrategy, lambda: _make_context(mode="bullish")),
        "RSIMeanReversion": StrategyCase(RSIMeanReversionStrategy, lambda: _make_context(mode="mean_reversion")),
        "BollingerBands": StrategyCase(BollingerBandsStrategy, lambda: _make_context(mode="mean_reversion")),
        "Breakout": StrategyCase(BreakoutStrategy, lambda: _make_context(mode="breakout")),
        "TrendPullback": StrategyCase(TrendPullbackStrategy, lambda: _make_context(mode="bullish")),
        "ORB": StrategyCase(ORBStrategy, lambda: _make_context(mode="bullish")),
    }


def main() -> int:
    cases = _strategy_cases()
    enabled = app_config.get_enabled_strategies()
    
    print(f"Running mock strategy smoke-tests for {len(enabled)} enabled strategies...")
    failures: List[Tuple[str, str]] = []
    
    for cfg in enabled:
        case = cases.get(cfg.name)
        if not case:
            print(f"⚠️  Skipping {cfg.name}: no mock harness defined")
            continue
        
        strategy = case.cls(cfg.name, cfg.params)
        context = case.context_builder()
        
        try:
            signals = strategy.generate_signals(context)
            print(f"✅ {cfg.name}: ran OK (signals={len(signals)})")
        except Exception as exc:  # pragma: no cover - defensive logging
            failures.append((cfg.name, str(exc)))
            print(f"❌ {cfg.name}: crashed -> {exc}")
    
    if failures:
        print("\nFailures:")
        for name, err in failures:
            print(f"- {name}: {err}")
        return 1
    
    print("\nAll strategy mocks completed without exceptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
