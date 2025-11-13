#!/usr/bin/env python3
"""Comprehensive test suite for AITRAPP trading application"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all core modules can be imported"""
    print("=" * 70)
    print("📦 Testing Module Imports")
    print("=" * 70)
    
    modules = [
        ("packages.core.config", "Config"),
        ("packages.core.models", "Models"),
        ("packages.core.risk", "Risk Management"),
        ("packages.core.execution", "Execution Engine"),
        ("packages.core.strategies.base", "Base Strategy"),
    ]
    
    results = []
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {description:30s} - OK")
            results.append((description, True, None))
        except Exception as e:
            print(f"❌ {description:30s} - FAILED: {e}")
            results.append((description, False, str(e)))
    
    print()
    return results


def test_config_loading():
    """Test configuration loading"""
    print("=" * 70)
    print("⚙️  Testing Configuration Loading")
    print("=" * 70)
    
    try:
        from packages.core.config import app_config, settings
        
        print(f"✅ Settings loaded")
        print(f"   Mode: {settings.app_mode.value}")
        print(f"   API Port: {settings.api_port}")
        print(f"   Timezone: {settings.app_timezone}")
        
        print(f"✅ App config loaded")
        print(f"   Strategies: {len(app_config.get_enabled_strategies())}")
        print(f"   Risk limits: {app_config.risk.per_trade_risk_pct}% per trade")
        
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_manager():
    """Test risk management functionality"""
    print("=" * 70)
    print("🛡️  Testing Risk Manager")
    print("=" * 70)
    
    try:
        from packages.core.risk import RiskManager
        from packages.core.config import app_config
        
        risk_manager = RiskManager(app_config.risk)
        
        print(f"✅ Risk manager initialized")
        print(f"   Per-trade risk: {app_config.risk.per_trade_risk_pct}%")
        print(f"   Max portfolio heat: {app_config.risk.max_portfolio_heat_pct}%")
        print(f"   Daily loss stop: {app_config.risk.daily_loss_stop_pct}%")
        
        return True
    except Exception as e:
        print(f"❌ Risk manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategies():
    """Test strategy initialization"""
    print("=" * 70)
    print("📊 Testing Strategy Initialization")
    print("=" * 70)
    
    try:
        from packages.core.config import app_config
        from packages.core.strategies import ORBStrategy, TrendPullbackStrategy, OptionsRankerStrategy
        
        strategies_loaded = 0
        
        for strategy_config in app_config.get_enabled_strategies():
            try:
                if strategy_config.name == "ORB":
                    strategy = ORBStrategy(strategy_config.name, strategy_config.params)
                    print(f"✅ {strategy_config.name:20s} - Loaded")
                    strategies_loaded += 1
                elif strategy_config.name == "TrendPullback":
                    strategy = TrendPullbackStrategy(strategy_config.name, strategy_config.params)
                    print(f"✅ {strategy_config.name:20s} - Loaded")
                    strategies_loaded += 1
                elif strategy_config.name == "OptionsRanker":
                    strategy = OptionsRankerStrategy(strategy_config.name, strategy_config.params)
                    print(f"✅ {strategy_config.name:20s} - Loaded")
                    strategies_loaded += 1
            except Exception as e:
                print(f"❌ {strategy_config.name:20s} - Failed: {e}")
        
        print(f"\n✅ Loaded {strategies_loaded} strategies")
        return strategies_loaded > 0
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_historical_data():
    """Test historical data availability"""
    print("=" * 70)
    print("📈 Testing Historical Data Availability")
    print("=" * 70)
    
    data_dir = Path("docs/NSE OPINONS DATA")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False
    
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {data_dir}")
        return False
    
    print(f"✅ Found {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        size_mb = csv_file.stat().st_size / (1024 * 1024)
        print(f"   {csv_file.name:50s} ({size_mb:.2f} MB)")
    
    return True


def test_backtest_engine():
    """Test backtest engine initialization"""
    print("=" * 70)
    print("🧪 Testing Backtest Engine")
    print("=" * 70)
    
    try:
        from packages.core.backtest import BacktestEngine
        
        engine = BacktestEngine(
            initial_capital=1000000,
            data_dir="docs/NSE OPINONS DATA"
        )
        
        print(f"✅ Backtest engine initialized")
        print(f"   Initial capital: ₹1,000,000")
        print(f"   Data directory: docs/NSE OPINONS DATA")
        
        return True
    except Exception as e:
        print(f"❌ Backtest engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_iron_condor():
    """Test Iron Condor strategy"""
    print("=" * 70)
    print("🦅 Testing Iron Condor Strategy")
    print("=" * 70)
    
    try:
        from packages.core.strategies.iron_condor import IronCondorStrategy
        
        params = {
            "call_spread_width": 200,
            "put_spread_width": 200,
            "call_short_strike_offset": 200,
            "put_short_strike_offset": 200,
            "max_dte": 20,
            "min_dte": 9,
            "target_profit_pct": 50,
            "max_loss_pct": 200,
            "iv_percentile_min": 30,
            "iv_percentile_max": 70,
            "max_positions": 2
        }
        
        strategy = IronCondorStrategy("IronCondor", params)
        print(f"✅ Iron Condor strategy initialized")
        print(f"   Strategy name: {strategy.name}")
        print(f"   Max positions: {params['max_positions']}")
        
        return True
    except Exception as e:
        print(f"❌ Iron Condor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("🚀 AITRAPP Trading Application - Comprehensive Test Suite")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Run tests
    results["imports"] = test_imports()
    print()
    
    results["config"] = test_config_loading()
    print()
    
    results["risk"] = test_risk_manager()
    print()
    
    results["strategies"] = test_strategies()
    print()
    
    results["historical_data"] = test_historical_data()
    print()
    
    results["backtest"] = test_backtest_engine()
    print()
    
    results["iron_condor"] = test_iron_condor()
    print()
    
    # Summary
    print("=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10s} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
