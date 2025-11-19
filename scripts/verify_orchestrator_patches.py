#!/usr/bin/env python3
"""
Verification script for orchestrator patches.

Checks:
1. Token limit is configurable (default 80)
2. Strategy priority ordering works
3. StrategyContext has regime/event fields

Usage:
    python3 scripts/verify_orchestrator_patches.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_patch_1_token_limit():
    """Test Patch 1: Configurable token limit"""
    print("🔍 Testing Patch 1: Token Limit...")
    
    # Test default
    os.environ.pop("MAX_TOKENS_PER_SCAN", None)
    from packages.core.orchestrator import TradingOrchestrator
    from unittest.mock import MagicMock
    
    # Create minimal orchestrator instance
    orchestrator = TradingOrchestrator(
        kite=MagicMock(),
        strategies=[],
        instrument_manager=MagicMock(),
        market_data_stream=MagicMock(),
        risk_manager=MagicMock(),
        execution_engine=MagicMock(),
        exit_manager=MagicMock(),
        ranker=MagicMock()
    )
    
    default_limit = orchestrator.max_tokens_per_scan
    assert default_limit == 80, f"Expected default 80, got {default_limit}"
    print(f"  ✅ Default token limit: {default_limit}")
    
    # Test custom limit
    os.environ["MAX_TOKENS_PER_SCAN"] = "120"
    orchestrator2 = TradingOrchestrator(
        kite=MagicMock(),
        strategies=[],
        instrument_manager=MagicMock(),
        market_data_stream=MagicMock(),
        risk_manager=MagicMock(),
        execution_engine=MagicMock(),
        exit_manager=MagicMock(),
        ranker=MagicMock()
    )
    custom_limit = orchestrator2.max_tokens_per_scan
    assert custom_limit == 120, f"Expected 120, got {custom_limit}"
    print(f"  ✅ Custom token limit: {custom_limit}")
    
    print("  ✅ Patch 1 verified\n")
    return True


def test_patch_2_priority_ordering():
    """Test Patch 2: Strategy priority ordering"""
    print("🔍 Testing Patch 2: Priority Ordering...")
    
    from packages.core.orchestrator import TradingOrchestrator
    from packages.core.strategies.base import Strategy
    from unittest.mock import MagicMock
    
    # Create mock strategies with different priorities
    class MockStrategy(Strategy):
        def generate_signals(self, context):
            return []
    
    strat1 = MockStrategy("Strategy1", {})
    strat1.priority = 10
    strat1.enabled = True
    
    strat2 = MockStrategy("Strategy2", {})
    strat2.priority = 5
    strat2.enabled = True
    
    strat3 = MockStrategy("Strategy3", {})
    strat3.priority = 20
    strat3.enabled = True
    
    strat4 = MockStrategy("Strategy4", {})
    # No priority set (should default to 100)
    strat4.enabled = True
    
    orchestrator = TradingOrchestrator(
        kite=MagicMock(),
        strategies=[strat1, strat2, strat3, strat4],
        instrument_manager=MagicMock(),
        market_data_stream=MagicMock(),
        risk_manager=MagicMock(),
        execution_engine=MagicMock(),
        exit_manager=MagicMock(),
        ranker=MagicMock()
    )
    
    sorted_strategies = orchestrator._sorted_strategies()
    priorities = [getattr(s, 'priority', 100) for s in sorted_strategies]
    
    # Should be sorted: 5, 10, 20, 100
    assert priorities == [5, 10, 20, 100], f"Expected [5, 10, 20, 100], got {priorities}"
    print(f"  ✅ Strategies sorted by priority: {priorities}")
    print(f"  ✅ Order: {[s.name for s in sorted_strategies]}")
    
    print("  ✅ Patch 2 verified\n")
    return True


def test_patch_3_strategy_context():
    """Test Patch 3: StrategyContext enrichment"""
    print("🔍 Testing Patch 3: StrategyContext Enrichment...")
    
    from packages.core.strategies.base import StrategyContext
    from packages.core.models import Instrument, InstrumentType
    from datetime import datetime
    import inspect
    
    # Check StrategyContext has new fields
    sig = inspect.signature(StrategyContext.__init__)
    params = list(sig.parameters.keys())
    
    required_fields = ['regime_snapshot', 'event_snapshot', 'universe_size', 'token_count']
    missing = [f for f in required_fields if f not in params]
    
    if missing:
        print(f"  ❌ Missing fields: {missing}")
        print(f"  Found params: {params}")
        return False
    
    print(f"  ✅ StrategyContext has all required fields: {required_fields}")
    
    # Test creating context with new fields
    instrument = Instrument(
        token=12345,
        symbol="NIFTY",
        tradingsymbol="NIFTY 50",
        exchange="NSE",
        instrument_type=InstrumentType.EQ
    )
    
    context = StrategyContext(
        timestamp=datetime.now(),
        instrument=instrument,
        regime_snapshot={"NIFTY": {"regime": "LOW_MEAN_REVERT"}},
        event_snapshot={"today": {"has_major_event": False}},
        universe_size=400,
        token_count=80
    )
    
    assert context.regime_snapshot is not None
    assert context.event_snapshot is not None
    assert context.universe_size == 400
    assert context.token_count == 80
    
    print(f"  ✅ Context created with regime: {context.regime_snapshot}")
    print(f"  ✅ Context created with event: {context.event_snapshot}")
    print(f"  ✅ Context created with universe_size: {context.universe_size}")
    print(f"  ✅ Context created with token_count: {context.token_count}")
    
    print("  ✅ Patch 3 verified\n")
    return True


def main():
    """Run all patch verification tests"""
    print("=" * 60)
    print("ORCHESTRATOR PATCHES VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    
    try:
        results.append(("Patch 1: Token Limit", test_patch_1_token_limit()))
    except Exception as e:
        print(f"  ❌ Patch 1 failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 1: Token Limit", False))
    
    try:
        results.append(("Patch 2: Priority Ordering", test_patch_2_priority_ordering()))
    except Exception as e:
        print(f"  ❌ Patch 2 failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 2: Priority Ordering", False))
    
    try:
        results.append(("Patch 3: StrategyContext", test_patch_3_strategy_context()))
    except Exception as e:
        print(f"  ❌ Patch 3 failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 3: StrategyContext", False))
    
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All patches verified successfully!")
        print("\nNext steps:")
        print("1. Test with API: python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000")
        print("2. Check logs for: '[Orchestrator] Scan cycle at ..., universe=400, using=80 tokens'")
        print("3. Verify priorities: curl -s http://localhost:8000/api/strategies/summary | jq '.strategies[] | {name, priority}'")
    else:
        print("⚠️  Some patches failed verification. Check errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

