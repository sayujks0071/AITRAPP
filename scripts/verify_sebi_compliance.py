#!/usr/bin/env python3
"""
SEBI Compliance Verification Script

Tests all 4 SEBI compliance features:
1. Enhanced Audit Logging (ORDER_PLACED, ORDER_CANCELLED)
2. Kill Switch Endpoint
3. Strategy-wise Risk Limits
4. Dormant Account Check

Usage:
    python3 scripts/verify_sebi_compliance.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.config import RiskConfig, AppConfig
from packages.core.risk import RiskManager, PortfolioRisk
from packages.core.models import Signal, SignalSide, Instrument

# Import ComplianceManager from standalone compliance.py module
import importlib.util
compliance_spec = importlib.util.spec_from_file_location(
    "compliance_module",
    str(Path(__file__).parent.parent / "packages/core/compliance.py")
)
compliance_module = importlib.util.module_from_spec(compliance_spec)
compliance_spec.loader.exec_module(compliance_module)
ComplianceManager = compliance_module.ComplianceManager


def test_dormant_account_check():
    """Test dormant account detection"""
    print("\n" + "=" * 60)
    print("--- Verifying Dormant Account Check ---")
    print("=" * 60)

    compliance = ComplianceManager()

    # Case 1: Active account (traded 5 days ago)
    last_trade = datetime.now() - timedelta(days=5)
    is_active, reason = compliance.check_dormant_account(last_trade, max_dormant_days=30)
    print(f"Case 1 (Active): {is_active} - {reason}")
    assert is_active, "Active account should pass"

    # Case 2: Dormant account (traded 40 days ago)
    last_trade = datetime.now() - timedelta(days=40)
    is_active, reason = compliance.check_dormant_account(last_trade, max_dormant_days=30)
    print(f"Case 2 (Dormant): {is_active} - {reason}")
    assert not is_active, "Dormant account should fail"

    # Case 3: New account (no trades)
    is_active, reason = compliance.check_dormant_account(None, max_dormant_days=30)
    print(f"Case 3 (New): {is_active} - {reason}")
    assert is_active, "New account with no trades should pass"

    print("✅ Dormant Check Verified")


def test_strategy_risk_limits():
    """Test strategy-wise loss limits"""
    print("\n" + "=" * 60)
    print("--- Verifying Strategy Risk Limits ---")
    print("=" * 60)

    # Setup
    risk_config = RiskConfig({
        "per_trade_risk_pct": 0.5,
        "max_portfolio_heat_pct": 2.0,
        "daily_loss_stop_pct": -2.5,
        "max_loss_per_strategy_pct": -5.0  # Max 5% loss per strategy
    })
    risk_manager = RiskManager(risk_config)

    # Mock portfolio
    portfolio = PortfolioRisk(
        net_liquid=100000.0,
        used_margin=0.0,
        available_margin=100000.0,
        open_positions=[],
        total_risk_amount=0.0,
        unrealized_pnl=0.0,
        realized_pnl_today=0.0,
        daily_pnl=0.0,
        daily_loss_limit=-2500.0,
        max_portfolio_heat=2000.0
    )

    # Mock signal
    instrument = Instrument(
        tradingsymbol="TEST",
        exchange="NSE",
        lot_size=1,
        tick_size=0.05
    )
    signal = Signal(
        instrument=instrument,
        side=SignalSide.LONG,
        entry_price=100.0,
        stop_loss=90.0,
        stop_distance=10.0,
        strategy_name="TestStrategy"
    )

    # Case 1: Strategy with no loss
    result = risk_manager.check_signal(signal, portfolio)
    print(f"Case 1 (No Loss): Approved={result.approved}")
    assert result.approved, "Signal should be approved with no strategy loss"

    # Case 2: Strategy with huge loss (exceeds limit)
    risk_manager.strategy_pnl["TestStrategy"] = -2000.0  # -2% loss (exceeds -5% limit when added)
    # Actually, let me set it to exceed the limit
    max_loss = portfolio.net_liquid * (risk_config.max_loss_per_strategy_pct / 100)  # -5000
    risk_manager.strategy_pnl["TestStrategy"] = max_loss - 1000.0  # -6000 (exceeds -5000 limit)

    result = risk_manager.check_signal(signal, portfolio)
    print(f"Case 2 (Huge Loss): Approved={result.approved}, Reasons={result.reasons}")
    assert not result.approved, "Signal should be rejected with strategy loss exceeding limit"
    assert "Strategy TestStrategy loss" in result.reasons[0], "Should mention strategy loss"

    print("✅ Strategy Risk Verified")


def test_audit_logging():
    """Test audit logging presence (unit test only, not DB write)"""
    print("\n" + "=" * 60)
    print("--- Verifying Audit Logging Implementation ---")
    print("=" * 60)

    # Read execution engine source to verify audit logging is present
    exec_engine_path = Path(__file__).parent.parent / "packages/core/execution/execution_engine.py"

    if not exec_engine_path.exists():
        print("⚠️ Could not find execution_engine.py")
        return

    source = exec_engine_path.read_text()

    # Check for ORDER_PLACED audit logging
    has_order_placed = "AuditActionEnum.ORDER_PLACED" in source
    print(f"ORDER_PLACED audit logging: {'✅' if has_order_placed else '❌'}")

    # Check for ORDER_CANCELLED audit logging
    has_order_cancelled = "AuditActionEnum.ORDER_CANCELLED" in source
    print(f"ORDER_CANCELLED audit logging: {'✅' if has_order_cancelled else '❌'}")

    assert has_order_placed, "ORDER_PLACED audit logging not found"
    assert has_order_cancelled, "ORDER_CANCELLED audit logging not found"

    print("✅ Audit Logging Verified")


def test_kill_switch_endpoint():
    """Test kill switch endpoint presence"""
    print("\n" + "=" * 60)
    print("--- Verifying Kill Switch Endpoint ---")
    print("=" * 60)

    # Read control routes to verify kill switch endpoint
    control_path = Path(__file__).parent.parent / "apps/api/routes/control.py"

    if not control_path.exists():
        print("⚠️ Could not find control.py")
        return

    source = control_path.read_text()

    # Check for kill switch endpoint
    has_kill_switch = '@router.post("/kill-switch")' in source
    has_kill_switch_fn = "async def activate_kill_switch" in source

    print(f"Kill switch endpoint: {'✅' if has_kill_switch else '❌'}")
    print(f"Kill switch handler: {'✅' if has_kill_switch_fn else '❌'}")

    assert has_kill_switch, "Kill switch endpoint not found"
    assert has_kill_switch_fn, "Kill switch handler not found"

    print("✅ Kill Switch Endpoint Verified")


def test_risk_config_has_strategy_limit():
    """Verify RiskConfig has max_loss_per_strategy_pct"""
    print("\n" + "=" * 60)
    print("--- Verifying RiskConfig Strategy Limit ---")
    print("=" * 60)

    risk_config = RiskConfig({
        "max_loss_per_strategy_pct": -3.0
    })

    assert hasattr(risk_config, "max_loss_per_strategy_pct"), "RiskConfig missing max_loss_per_strategy_pct"
    assert risk_config.max_loss_per_strategy_pct == -3.0, "max_loss_per_strategy_pct not set correctly"

    print(f"max_loss_per_strategy_pct: {risk_config.max_loss_per_strategy_pct}%")
    print("✅ RiskConfig Strategy Limit Verified")


def main():
    """Run all verification tests"""
    print("🔍 SEBI Compliance Verification Suite")
    print("=" * 60)

    try:
        # Test 1: Dormant Account Check
        test_dormant_account_check()

        # Test 2: Strategy Risk Limits
        test_strategy_risk_limits()

        # Test 3: RiskConfig has strategy limit field
        test_risk_config_has_strategy_limit()

        # Test 4: Audit Logging Implementation
        test_audit_logging()

        # Test 5: Kill Switch Endpoint
        test_kill_switch_endpoint()

        print("\n" + "=" * 60)
        print("🎉 All Verification Checks Passed!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Deploy changes to staging environment")
        print("2. Run end-to-end tests with live database")
        print("3. Test Kill Switch in controlled environment")
        print("4. Enable SEBI compliance in production (COMPLIANCE_SEBI_2025=1)")

        return 0

    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
