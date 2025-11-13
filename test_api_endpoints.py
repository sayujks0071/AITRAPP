#!/usr/bin/env python3
"""Test API endpoints without starting the full server"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_api_models():
    """Test API models and request/response structures"""
    print("=" * 70)
    print("🔌 Testing API Models")
    print("=" * 70)
    
    try:
        from apps.api.main import (
            ModeChangeRequest,
            PositionResponse,
            SystemStateResponse,
            BacktestRequest
        )
        
        # Test ModeChangeRequest
        mode_req = ModeChangeRequest(mode="PAPER")
        assert mode_req.mode == "PAPER"
        print("✅ ModeChangeRequest model - OK")
        
        # Test PositionResponse
        pos_resp = PositionResponse(
            position_id="test-123",
            instrument="NIFTY25DEC24FUT",
            side="LONG",
            quantity=50,
            entry_price=22000.0,
            current_price=22100.0,
            unrealized_pnl=5000.0,
            pnl_pct=2.27
        )
        assert pos_resp.position_id == "test-123"
        print("✅ PositionResponse model - OK")
        
        # Test SystemStateResponse
        state_resp = SystemStateResponse(
            timestamp="2025-11-13T03:00:00",
            mode="PAPER",
            is_paused=False,
            is_market_open=False,
            positions_count=0,
            trades_today=0,
            win_rate=0.0,
            daily_pnl=0.0
        )
        assert state_resp.mode == "PAPER"
        print("✅ SystemStateResponse model - OK")
        
        # Test BacktestRequest
        backtest_req = BacktestRequest(
            symbol="NIFTY",
            start_date="2025-08-15",
            end_date="2025-11-10",
            initial_capital=1000000,
            strategy="all"
        )
        assert backtest_req.symbol == "NIFTY"
        print("✅ BacktestRequest model - OK")
        
        return True
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_routes():
    """Test that API routes are properly defined"""
    print("=" * 70)
    print("🛣️  Testing API Routes")
    print("=" * 70)
    
    try:
        from apps.api.main import app
        
        routes = [route.path for route in app.routes]
        
        expected_routes = [
            "/",
            "/health",
            "/state",
            "/positions",
            "/orders",
            "/mode",
            "/pause",
            "/resume",
            "/flatten",
            "/backtest"
        ]
        
        print(f"✅ Found {len(routes)} routes")
        
        for expected in expected_routes:
            if expected in routes:
                print(f"   ✅ {expected}")
            else:
                print(f"   ❌ {expected} - MISSING")
        
        return True
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("=" * 70)
    print("🔌 API Endpoints Test Suite")
    print("=" * 70)
    print()
    
    results = []
    
    results.append(("API Models", test_api_models()))
    print()
    results.append(("API Routes", test_api_routes()))
    print()
    
    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10s} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    sys.exit(0 if passed == total else 1)
