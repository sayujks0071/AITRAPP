# SEBI Compliance Operational Runbook

**Version:** 1.0
**Last Updated:** 2025-11-29
**Owner:** Trading Operations Team

---

## Table of Contents

1. [Overview](#overview)
2. [Compliance Features](#compliance-features)
3. [Configuration](#configuration)
4. [Daily Operations](#daily-operations)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Emergency Procedures](#emergency-procedures)
7. [Audit & Reporting](#audit--reporting)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This runbook covers the operational procedures for SEBI/NSE 2025 Retail Algo Trading Framework compliance features implemented in AITRAPP.

### Compliance Requirements

- ✅ Enhanced audit logging (all orders tracked)
- ✅ Kill switch (emergency stop)
- ✅ Strategy-wise risk limits
- ✅ Dormant account detection
- ✅ Rate limiting (<10 orders/second)
- ✅ OAuth token freshness
- ✅ Static IP verification (optional)

### Regulatory Context

**SEBI Feb 2025 Framework** mandates:
- Persistent audit trails (5-year retention)
- Emergency stop mechanisms
- Per-strategy risk controls
- Account activity monitoring

---

## Compliance Features

### 1. Enhanced Audit Logging

**Purpose:** Log all order placements and cancellations to database for regulatory audit.

**Implementation:**
- Location: `packages/core/execution/execution_engine.py`
- Database: `audit_logs` table
- Events: `ORDER_PLACED`, `ORDER_CANCELLED`

**What's Logged:**
```json
{
  "action": "ORDER_PLACED",
  "level": "INFO",
  "category": "EXEC",
  "message": "Order placed: BUY 75 NIFTY24DECFUT",
  "details": {
    "order_id": "241129000123456",
    "symbol": "NIFTY24DECFUT",
    "side": "BUY",
    "quantity": 75,
    "product": "NRML",
    "order_type": "LIMIT",
    "price": 19500.00,
    "tag": "STRAT_MOMENTUM",
    "exchange": "NFO"
  }
}
```

**Verification:**
```sql
-- Check recent audit logs
SELECT ts, action, message, details
FROM audit_logs
WHERE action IN ('ORDER_PLACED', 'ORDER_CANCELLED')
ORDER BY ts DESC
LIMIT 10;
```

---

### 2. Kill Switch Endpoint

**Purpose:** Emergency stop - pause trading and flatten all positions immediately.

**Endpoint:** `POST /control/kill-switch`

**Actions Performed:**
1. Pause all trading (blocks new signals)
2. Cancel all pending orders
3. Close all open positions (market orders)

**Usage:**

**Via API:**
```bash
curl -X POST http://localhost:8000/control/kill-switch \
  -H "Content-Type: application/json"
```

**Via Dashboard:**
- Navigate to Control Panel
- Click "🚨 EMERGENCY KILL SWITCH"
- Confirm action

**Response:**
```json
{
  "status": "KILLED",
  "closed_positions": 5,
  "cancelled_orders": 2,
  "message": "Trading halted, all positions closed"
}
```

**When to Use:**
- System behaving erratically
- Broker API issues
- Market disruption/halt
- Unauthorized access suspected
- Manual intervention required urgently

**Recovery:**
```bash
# Resume trading after investigation
curl -X POST http://localhost:8000/control/resume
```

---

### 3. Strategy-wise Risk Limits

**Purpose:** Prevent any single strategy from exceeding a loss threshold.

**Configuration:**
```yaml
# configs/app.yaml
risk:
  max_loss_per_strategy_pct: -5.0  # Max 5% loss per strategy
```

**Implementation:**
- Location: `packages/core/risk.py`
- Check: Before every signal approval
- Tracking: Per-strategy PnL accumulator

**How It Works:**
1. Strategy generates signal
2. RiskManager checks `strategy_pnl[strategy_name]`
3. If PnL < threshold → signal rejected
4. PnL updated when position closes

**Monitoring:**
```python
# Check strategy PnL
risk_manager = state.risk_manager
for strategy_name in ["MomentumStrategy", "MeanReversionStrategy"]:
    pnl = risk_manager.get_strategy_pnl(strategy_name)
    print(f"{strategy_name}: {pnl:.2f} INR")
```

**Alerts:**
- Strategy approaches 80% of loss limit → WARNING
- Strategy hits loss limit → CRITICAL (strategy blocked)

---

### 4. Dormant Account Check

**Purpose:** Detect and warn about accounts with no recent trading activity.

**Configuration:**
```python
# Default: 30 days
max_dormant_days = 30
```

**Implementation:**
- Location: `packages/core/compliance.py`
- Check: On system startup and daily
- Action: Log warning if account dormant

**Usage:**
```python
from packages.core.compliance import ComplianceManager

compliance = ComplianceManager()
last_trade_date = get_last_trade_date()  # From database
is_active, reason = compliance.check_dormant_account(
    last_trade_date,
    max_dormant_days=30
)

if not is_active:
    logger.warning(f"Dormant account detected: {reason}")
    send_alert(f"Account inactive: {reason}")
```

**Recommended Actions:**
- < 30 days: Normal operation
- 30-60 days: Send notification to account owner
- > 60 days: Require re-authentication before trading

---

## Configuration

### Environment Variables

```bash
# .env file

# Enable SEBI compliance mode
COMPLIANCE_SEBI_2025=1

# Exchange Algo ID (required post broker go-live)
EXCHANGE_ALGO_ID="ALGO12345"

# Rate limiting
TOPS_CAP_PER_SEC=9  # Must be < 10

# Optional: Static IP verification
REQUIRE_STATIC_IP=0
EXPECTED_EGRESS_IP="203.192.10.45"

# OAuth/2FA
OAUTH_REQUIRED=1
TWO_FA_REQUIRED=1

# Audit retention
AUDIT_RETENTION_YEARS=5
```

### Application Config

```yaml
# configs/app.yaml

execution:
  tops_cap_per_sec: 9  # Orders per second limit

risk:
  per_trade_risk_pct: 0.5
  max_portfolio_heat_pct: 2.0
  daily_loss_stop_pct: -2.5
  max_loss_per_strategy_pct: -5.0  # SEBI compliance
```

---

## Daily Operations

### Morning Startup Checklist

```bash
#!/bin/bash
# scripts/morning_compliance_check.sh

echo "🔍 SEBI Compliance Pre-Flight Check"

# 1. Verify compliance mode enabled
if [ "$COMPLIANCE_SEBI_2025" != "1" ]; then
    echo "❌ COMPLIANCE_SEBI_2025 not enabled"
    exit 1
fi

# 2. Check database connectivity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM audit_logs;" > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Database not accessible"
    exit 1
fi

# 3. Verify audit retention policy
python3 scripts/verify_audit_retention.py

# 4. Check dormant account status
python3 scripts/check_dormant_accounts.py

# 5. Verify kill switch endpoint
curl -s http://localhost:8000/control/state > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ API not running"
    exit 1
fi

# 6. Test rate limiter
python3 scripts/test_rate_limiter.py

echo "✅ All compliance checks passed"
```

### End-of-Day Checklist

```bash
#!/bin/bash
# scripts/eod_compliance_report.sh

echo "📊 End-of-Day Compliance Report"

# 1. Export audit logs
psql $DATABASE_URL -c "
  COPY (
    SELECT * FROM audit_logs
    WHERE ts >= CURRENT_DATE
  ) TO '/var/log/aitrapp/audit_$(date +%Y%m%d).csv' CSV HEADER;
"

# 2. Generate strategy PnL report
python3 scripts/generate_strategy_pnl_report.py

# 3. Check for compliance violations
python3 scripts/check_compliance_violations.py

# 4. Archive logs
./scripts/archive_logs.sh

echo "✅ EOD compliance report complete"
```

---

## Monitoring & Alerts

### Key Metrics

Monitor these in your dashboard:

1. **Audit Log Rate**
   - Metric: `audit_logs_per_minute`
   - Alert: < 0 (no logging = system issue)

2. **Strategy Loss Breaches**
   - Metric: `strategy_loss_breach_count`
   - Alert: > 0 (strategy hit loss limit)

3. **Kill Switch Activations**
   - Metric: `kill_switch_activation_count`
   - Alert: > 0 (emergency stop triggered)

4. **Rate Limit Violations**
   - Metric: `rate_limit_violations_per_hour`
   - Alert: > 5 (approaching SEBI limit)

5. **Dormant Account Detections**
   - Metric: `dormant_account_flags`
   - Alert: > 0 (account inactive)

### Alert Rules

```yaml
# alerts.yaml

- alert: StrategyLossLimitBreached
  expr: strategy_pnl{strategy=~".*"} < -5000
  severity: CRITICAL
  message: "Strategy {{ $labels.strategy }} exceeded loss limit"

- alert: AuditLoggingFailure
  expr: rate(audit_logs_total[5m]) == 0
  severity: CRITICAL
  message: "Audit logging stopped - compliance violation!"

- alert: KillSwitchActivated
  expr: kill_switch_active == 1
  severity: CRITICAL
  message: "EMERGENCY: Kill switch activated"

- alert: RateLimitApproaching
  expr: rate(orders_placed[60s]) > 8
  severity: WARNING
  message: "Order rate approaching 10 OPS SEBI limit"
```

---

## Emergency Procedures

### Scenario 1: Kill Switch Activation

**Immediate Actions:**
1. Verify all positions are closed
   ```bash
   curl http://localhost:8000/control/state | jq '.open_positions'
   ```

2. Check system logs for root cause
   ```bash
   tail -100 logs/aitrapp.log | grep -i error
   ```

3. Investigate trigger
   ```bash
   # Check audit logs for KILL_SWITCH action
   psql $DATABASE_URL -c "
     SELECT * FROM audit_logs
     WHERE action = 'KILL_SWITCH'
     ORDER BY ts DESC LIMIT 1;
   "
   ```

4. Resume only after investigation complete
   ```bash
   curl -X POST http://localhost:8000/control/resume
   ```

### Scenario 2: Strategy Loss Limit Breached

**Immediate Actions:**
1. Identify affected strategy
   ```python
   risk_manager.get_strategy_pnl("YourStrategy")
   ```

2. Review recent trades
   ```sql
   SELECT * FROM positions
   WHERE strategy = 'YourStrategy'
   AND closed_at >= CURRENT_DATE
   ORDER BY closed_at DESC;
   ```

3. Analyze root cause
   - Market conditions changed?
   - Strategy parameters need adjustment?
   - Bug in strategy logic?

4. Decision: Fix and re-enable OR disable strategy
   ```yaml
   # configs/app.yaml
   strategies:
     - name: YourStrategy
       enabled: false  # Disable until fixed
   ```

### Scenario 3: Audit Logging Failure

**Immediate Actions:**
1. **CRITICAL:** Trading MUST stop if audit logging fails
   ```bash
   curl -X POST http://localhost:8000/control/pause
   ```

2. Check database connectivity
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

3. Check disk space
   ```bash
   df -h /var/lib/postgresql
   ```

4. Verify database permissions
   ```sql
   SELECT * FROM information_schema.table_privileges
   WHERE table_name = 'audit_logs';
   ```

5. Only resume after logging is restored and verified
   ```bash
   python3 scripts/test_audit_logging.py
   ```

---

## Audit & Reporting

### SEBI Audit Export

```python
#!/usr/bin/env python3
# scripts/export_sebi_audit.py
"""
Export SEBI-compliant audit trail for regulatory submission.
"""

import psycopg2
import csv
from datetime import datetime, timedelta

def export_audit_trail(start_date, end_date, output_file):
    """Export audit logs for date range"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    query = """
        SELECT
            ts,
            action,
            category,
            message,
            details::text,
            correlation_id,
            config_sha
        FROM audit_logs
        WHERE ts >= %s AND ts < %s
        AND action IN ('ORDER_PLACED', 'ORDER_CANCELLED',
                       'KILL_SWITCH', 'MODE_CHANGE')
        ORDER BY ts ASC
    """

    cur.execute(query, (start_date, end_date))

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Action', 'Category',
                        'Message', 'Details', 'CorrelationID', 'ConfigSHA'])
        writer.writerows(cur)

    print(f"✅ Exported {cur.rowcount} audit records to {output_file}")

    conn.close()

if __name__ == "__main__":
    # Export last month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    output = f"audit_trail_{start_date:%Y%m%d}_{end_date:%Y%m%d}.csv"
    export_audit_trail(start_date, end_date, output)
```

### Monthly Compliance Report

```bash
#!/bin/bash
# scripts/monthly_compliance_report.sh

MONTH=$(date +%Y-%m)

echo "📊 Generating Monthly Compliance Report for ${MONTH}"

# 1. Strategy Performance & Risk
psql $DATABASE_URL > "reports/strategy_risk_${MONTH}.csv" <<EOF
SELECT
    strategy,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(pnl) as total_pnl,
    MIN(pnl) as max_loss,
    MAX(pnl) as max_win
FROM positions
WHERE closed_at >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY strategy
ORDER BY total_pnl DESC;
EOF

# 2. Audit Log Summary
psql $DATABASE_URL > "reports/audit_summary_${MONTH}.csv" <<EOF
SELECT
    action,
    DATE(ts) as trade_date,
    COUNT(*) as count
FROM audit_logs
WHERE ts >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY action, DATE(ts)
ORDER BY trade_date DESC, action;
EOF

# 3. Kill Switch Activations
psql $DATABASE_URL > "reports/kill_switch_${MONTH}.csv" <<EOF
SELECT * FROM audit_logs
WHERE action = 'KILL_SWITCH'
AND ts >= DATE_TRUNC('month', CURRENT_DATE)
ORDER BY ts DESC;
EOF

# 4. Rate Limit Violations
grep "Rate limit" logs/aitrapp.log | grep "${MONTH}" > "reports/rate_limit_violations_${MONTH}.log"

echo "✅ Compliance report generated in reports/"
```

---

## Troubleshooting

### Issue: Audit Logs Not Being Written

**Symptoms:**
- No entries in `audit_logs` table
- Warning: "Failed to write ORDER_PLACED audit log"

**Diagnosis:**
```bash
# 1. Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# 2. Verify table exists
psql $DATABASE_URL -c "\d audit_logs"

# 3. Check permissions
psql $DATABASE_URL -c "
  SELECT * FROM information_schema.table_privileges
  WHERE table_name = 'audit_logs' AND grantee = CURRENT_USER;
"

# 4. Test manual insert
psql $DATABASE_URL -c "
  INSERT INTO audit_logs (action, level, category, message, details)
  VALUES ('TEST', 'INFO', 'EXEC', 'Test message', '{}');
"
```

**Solutions:**
- Grant INSERT permission: `GRANT INSERT ON audit_logs TO trader;`
- Run migrations: `alembic upgrade head`
- Check disk space: `df -h`

---

### Issue: Strategy Loss Limit Not Enforced

**Symptoms:**
- Strategy continues trading despite losses exceeding limit
- No "RISK VETO: STRATEGY_LOSS_LIMIT" warnings

**Diagnosis:**
```python
# Check RiskManager state
risk_manager = state.risk_manager
print(f"Config: {risk_manager.config.max_loss_per_strategy_pct}")
print(f"Strategy PnL: {risk_manager.strategy_pnl}")
```

**Solutions:**
- Verify `max_loss_per_strategy_pct` is set in config
- Ensure `update_strategy_pnl()` is called when positions close
- Check that `check_signal()` is called before order placement

---

### Issue: Kill Switch Not Responding

**Symptoms:**
- POST /control/kill-switch returns error
- Positions not closing after kill switch activation

**Diagnosis:**
```bash
# 1. Check API logs
tail -50 logs/uvicorn.log | grep kill-switch

# 2. Verify endpoint exists
curl -i http://localhost:8000/control/kill-switch

# 3. Check system state
curl http://localhost:8000/control/state | jq '.is_paused'
```

**Solutions:**
- Restart API server
- Verify `kill_switch()` method exists in AppState
- Check broker API connectivity
- Manually close positions if needed

---

## Appendix

### Compliance Checklist

**Pre-Go-Live:**
- [ ] All 4 SEBI features implemented and tested
- [ ] Audit logging verified with database writes
- [ ] Kill switch tested in staging
- [ ] Strategy loss limits configured
- [ ] Dormant account check enabled
- [ ] `COMPLIANCE_SEBI_2025=1` in production
- [ ] Monitoring and alerts configured
- [ ] Operational runbook reviewed by team
- [ ] Emergency contacts documented

**Daily:**
- [ ] Morning compliance check passed
- [ ] Audit logs being written
- [ ] No rate limit violations
- [ ] Strategy PnLs within limits
- [ ] No kill switch activations (unless intentional)
- [ ] EOD report generated

**Weekly:**
- [ ] Review strategy performance and risk
- [ ] Check for dormant accounts
- [ ] Verify audit log retention policy
- [ ] Test kill switch in staging (not production)

**Monthly:**
- [ ] Generate compliance report
- [ ] Export audit trail for archival
- [ ] Review alert effectiveness
- [ ] Update runbook if needed

---

## Contact & Escalation

**Tier 1 - Operations Team:**
- Trading hours monitoring
- Daily compliance checks
- Alert response

**Tier 2 - Engineering Team:**
- System issues
- Kill switch failures
- Audit logging problems

**Tier 3 - Compliance Officer:**
- Regulatory questions
- Audit submissions
- Policy decisions

**Emergency Escalation:**
1. Kill switch activation → Notify all tiers immediately
2. Audit logging failure → STOP TRADING → Escalate to Tier 2
3. Strategy loss breach → Tier 1 investigation, escalate if systemic

---

**Document End**
