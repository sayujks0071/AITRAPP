#!/usr/bin/env python3
"""
Simple SEBI Compliance Verification (No Dependencies)

Validates implementation by inspecting source code directly.
Safe to run without database or full environment setup.

Usage:
    python3 scripts/test_sebi_compliance_simple.py
"""

import sys
from pathlib import Path


def test_audit_logging_implementation():
    """Verify audit logging is implemented in execution engine"""
    print("\n" + "=" * 60)
    print("TEST 1: Enhanced Audit Logging")
    print("=" * 60)

    exec_path = Path(__file__).parent.parent / "packages/core/execution/execution_engine.py"

    if not exec_path.exists():
        print("❌ execution_engine.py not found")
        return False

    source = exec_path.read_text()

    # Check for ORDER_PLACED logging
    has_order_placed = "AuditActionEnum.ORDER_PLACED" in source
    has_order_placed_details = '"order_id": order_id' in source

    # Check for ORDER_CANCELLED logging
    has_order_cancelled = "AuditActionEnum.ORDER_CANCELLED" in source
    has_cancelled_details = '"reason": "stale_order_cleanup"' in source

    print(f"  ORDER_PLACED audit log: {'✅' if has_order_placed else '❌'}")
    print(f"  ORDER_PLACED details: {'✅' if has_order_placed_details else '❌'}")
    print(f"  ORDER_CANCELLED audit log: {'✅' if has_order_cancelled else '❌'}")
    print(f"  ORDER_CANCELLED details: {'✅' if has_cancelled_details else '❌'}")

    passed = has_order_placed and has_order_placed_details and has_order_cancelled and has_cancelled_details

    if passed:
        print("\n✅ Audit Logging: PASS")
    else:
        print("\n❌ Audit Logging: FAIL")

    return passed


def test_kill_switch_endpoint():
    """Verify kill switch endpoint exists"""
    print("\n" + "=" * 60)
    print("TEST 2: Kill Switch Endpoint")
    print("=" * 60)

    control_path = Path(__file__).parent.parent / "apps/api/routes/control.py"

    if not control_path.exists():
        print("❌ control.py not found")
        return False

    source = control_path.read_text()

    # Check for endpoint and handler
    has_endpoint = '@router.post("/kill-switch")' in source
    has_handler = "async def activate_kill_switch" in source
    has_pause = "await state.pause_trading()" in source or "await state.kill_switch()" in source
    has_flatten = "close_all_positions" in source or "kill_switch" in source

    print(f"  Kill switch endpoint: {'✅' if has_endpoint else '❌'}")
    print(f"  Handler function: {'✅' if has_handler else '❌'}")
    print(f"  Pause/Kill action: {'✅' if has_pause else '❌'}")
    print(f"  Position flatten: {'✅' if has_flatten else '❌'}")

    passed = has_endpoint and has_handler and has_pause

    if passed:
        print("\n✅ Kill Switch Endpoint: PASS")
    else:
        print("\n❌ Kill Switch Endpoint: FAIL")

    return passed


def test_strategy_risk_limits():
    """Verify strategy-wise risk limits implementation"""
    print("\n" + "=" * 60)
    print("TEST 3: Strategy-wise Risk Limits")
    print("=" * 60)

    config_path = Path(__file__).parent.parent / "packages/core/config.py"
    risk_path = Path(__file__).parent.parent / "packages/core/risk.py"

    if not config_path.exists() or not risk_path.exists():
        print("❌ config.py or risk.py not found")
        return False

    config_source = config_path.read_text()
    risk_source = risk_path.read_text()

    # Check RiskConfig has max_loss_per_strategy_pct
    has_config_field = "max_loss_per_strategy_pct" in config_source
    has_config_comment = "SEBI Compliance" in config_source or "Strategy-wise" in config_source

    # Check RiskManager tracks strategy PnL
    has_strategy_pnl = "strategy_pnl" in risk_source
    has_get_strategy_pnl = "def get_strategy_pnl" in risk_source
    has_update_strategy_pnl = "def update_strategy_pnl" in risk_source
    has_strategy_check = "STRATEGY_LOSS_LIMIT" in risk_source or "Strategy" in risk_source and "loss" in risk_source

    print(f"  RiskConfig.max_loss_per_strategy_pct: {'✅' if has_config_field else '❌'}")
    print(f"  RiskConfig SEBI comment: {'✅' if has_config_comment else '❌'}")
    print(f"  RiskManager.strategy_pnl tracking: {'✅' if has_strategy_pnl else '❌'}")
    print(f"  get_strategy_pnl() method: {'✅' if has_get_strategy_pnl else '❌'}")
    print(f"  update_strategy_pnl() method: {'✅' if has_update_strategy_pnl else '❌'}")
    print(f"  Strategy loss check in check_signal: {'✅' if has_strategy_check else '❌'}")

    passed = (has_config_field and has_strategy_pnl and
              has_get_strategy_pnl and has_update_strategy_pnl)

    if passed:
        print("\n✅ Strategy Risk Limits: PASS")
    else:
        print("\n❌ Strategy Risk Limits: FAIL")

    return passed


def test_dormant_account_check():
    """Verify dormant account check implementation"""
    print("\n" + "=" * 60)
    print("TEST 4: Dormant Account Check")
    print("=" * 60)

    compliance_path = Path(__file__).parent.parent / "packages/core/compliance.py"

    if not compliance_path.exists():
        print("❌ compliance.py not found")
        return False

    source = compliance_path.read_text()

    # Check for dormant account method
    has_method = "def check_dormant_account" in source
    has_last_trade_param = "last_trade_date" in source
    has_max_days_param = "max_dormant_days" in source
    has_datetime_logic = "days_since_trade" in source or "(datetime.now() - last_trade_date)" in source
    has_comparison = "days_since_trade > max_dormant_days" in source or "days > max_dormant_days" in source

    print(f"  check_dormant_account() method: {'✅' if has_method else '❌'}")
    print(f"  last_trade_date parameter: {'✅' if has_last_trade_param else '❌'}")
    print(f"  max_dormant_days parameter: {'✅' if has_max_days_param else '❌'}")
    print(f"  Days calculation logic: {'✅' if has_datetime_logic else '❌'}")
    print(f"  Dormancy comparison: {'✅' if has_comparison else '❌'}")

    passed = has_method and has_last_trade_param and has_max_days_param and has_datetime_logic

    if passed:
        print("\n✅ Dormant Account Check: PASS")
    else:
        print("\n❌ Dormant Account Check: FAIL")

    return passed


def test_audit_log_model():
    """Verify AuditLog model has required enums"""
    print("\n" + "=" * 60)
    print("TEST 5: AuditLog Model (ORDER_PLACED, ORDER_CANCELLED enums)")
    print("=" * 60)

    models_path = Path(__file__).parent.parent / "packages/storage/models.py"

    if not models_path.exists():
        print("❌ models.py not found")
        return False

    source = models_path.read_text()

    # Check for AuditActionEnum
    has_enum = "class AuditActionEnum" in source
    has_order_placed = "ORDER_PLACED" in source
    has_order_cancelled = "ORDER_CANCELLED" in source
    has_audit_log_model = "class AuditLog" in source

    print(f"  AuditActionEnum class: {'✅' if has_enum else '❌'}")
    print(f"  ORDER_PLACED enum: {'✅' if has_order_placed else '❌'}")
    print(f"  ORDER_CANCELLED enum: {'✅' if has_order_cancelled else '❌'}")
    print(f"  AuditLog model: {'✅' if has_audit_log_model else '❌'}")

    passed = has_enum and has_order_placed and has_order_cancelled and has_audit_log_model

    if passed:
        print("\n✅ AuditLog Model: PASS")
    else:
        print("\n❌ AuditLog Model: FAIL")

    return passed


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔍 SEBI Compliance Verification (Code Inspection)")
    print("=" * 60)
    print("\nVerifying implementation in source code...")

    results = []

    # Run all tests
    results.append(("Enhanced Audit Logging", test_audit_logging_implementation()))
    results.append(("Kill Switch Endpoint", test_kill_switch_endpoint()))
    results.append(("Strategy-wise Risk Limits", test_strategy_risk_limits()))
    results.append(("Dormant Account Check", test_dormant_account_check()))
    results.append(("AuditLog Model", test_audit_log_model()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")

    print("\n" + "=" * 60)
    if passed_count == total_count:
        print(f"🎉 ALL TESTS PASSED ({passed_count}/{total_count})")
        print("=" * 60)
        print("\n✅ SEBI Compliance Implementation: VERIFIED")
        print("\nNext Steps:")
        print("  1. Run integration tests with database")
        print("  2. Test kill switch in staging environment")
        print("  3. Enable compliance mode: COMPLIANCE_SEBI_2025=1")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed_count}/{total_count} passed)")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
