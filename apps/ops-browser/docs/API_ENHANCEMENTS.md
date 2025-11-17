# API Enhancements for Ops Browser

## Recommended API Changes

### 1. Flatten Endpoint Security

**Add to `apps/api/main.py`:**

```python
from fastapi import Header, HTTPException, Request
from collections import defaultdict
import time
import os
import structlog

logger = structlog.get_logger(__name__)

# Rate limit tracking
flatten_attempts = defaultdict(list)
flatten_lockouts = defaultdict(float)

OPS_KEY = os.getenv("OPS_KEY", "")
OPS_PIN = os.getenv("OPS_PIN", "")

@app.post("/flatten")
async def flatten_all(
    request: Request,
    reason: str = "manual",
    ops_pin: Optional[str] = None,
    x_ops_key: Optional[str] = Header(None, alias="X-Ops-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    """Flatten all positions with security guards"""
    from packages.core.metrics import (
        ui_flatten_clicks_total,
        ui_flatten_confirms_total,
        flatten_requests_total,
        flatten_duration_seconds,
    )
    
    client_ip = request.client.host
    req_id = x_request_id or f"req_{int(time.time())}"
    
    # Check lockout
    if time.time() < flatten_lockouts.get(client_ip, 0):
        flatten_requests_total.labels(result="rate_limited").inc()
        logger.warning("Flatten rate limited (lockout)", ip=client_ip, req_id=req_id)
        raise HTTPException(429, "Rate limited: too many failed attempts")
    
    # Check header
    if not x_ops_key or x_ops_key != OPS_KEY:
        _record_failed_attempt(client_ip)
        flatten_requests_total.labels(result="error").inc()
        logger.warning("Flatten rejected: invalid key", ip=client_ip, req_id=req_id)
        raise HTTPException(403, "Invalid X-Ops-Key")
    
    # Check PIN (optional)
    if OPS_PIN and ops_pin != OPS_PIN:
        _record_failed_attempt(client_ip)
        flatten_requests_total.labels(result="error").inc()
        logger.warning("Flatten rejected: invalid PIN", ip=client_ip, req_id=req_id)
        raise HTTPException(403, "Invalid ops PIN")
    
    # Rate limit: 1 per 10s
    now = time.time()
    attempts = flatten_attempts[client_ip]
    attempts = [t for t in attempts if now - t < 10]
    
    if len(attempts) >= 1:
        flatten_requests_total.labels(result="rate_limited").inc()
        logger.warning("Flatten rate limited", ip=client_ip, req_id=req_id)
        raise HTTPException(429, "Rate limited: 1 flatten per 10s")
    
    attempts.append(now)
    flatten_attempts[client_ip] = attempts
    
    # Record metrics
    ui_flatten_confirms_total.inc()
    flatten_requests_total.labels(result="ok").inc()
    
    # Audit log
    positions_before = len([p for p in app_state.positions if p.is_open])
    
    start_time = time.time()
    try:
        # Existing flatten logic
        if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE") and app_state.crypto_router:
            orders = await app_state.crypto_router.flatten()
            duration = time.time() - start_time
            venue = getattr(app_state.crypto_router, 'venue', None)
            if venue:
                flatten_duration_seconds.labels(venue=venue.value).observe(duration)
        else:
            if app_state.orchestrator:
                await app_state.orchestrator.flatten_all(reason=reason)
                duration = time.time() - start_time
        
        positions_after = len([p for p in app_state.positions if p.is_open])
        
        # Structured audit log
        audit_log.info({
            "ts": datetime.utcnow().isoformat(),
            "actor": "web",
            "ip": client_ip,
            "route": "/flatten",
            "mode": settings.app_mode.value,
            "positions_before": positions_before,
            "positions_after": positions_after,
            "duration_ms": int(duration * 1000),
            "result": "ok",
            "req_id": req_id,
            "user_agent": request.headers.get("user-agent", "unknown"),
        })
        
        return {
            "status": "flattened",
            "reason": reason,
            "duration_seconds": round(duration, 3),
            "positions_before": positions_before,
            "positions_after": positions_after,
            "req_id": req_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        flatten_requests_total.labels(result="error").inc()
        logger.error("Flatten failed", error=str(e), req_id=req_id, ip=client_ip)
        raise HTTPException(500, f"Flatten failed: {str(e)}")

def _record_failed_attempt(client_ip: str):
    """Record failed attempt and lockout if needed"""
    now = time.time()
    attempts = flatten_attempts[client_ip]
    attempts.append(now)
    
    # Keep only last 3 attempts
    attempts = attempts[-3:]
    flatten_attempts[client_ip] = attempts
    
    # Lockout after 3 failures in 60s
    if len(attempts) >= 3 and (now - attempts[0]) < 60:
        flatten_lockouts[client_ip] = now + 60
        logger.warning("Flatten lockout activated", ip=client_ip, duration=60)
```

### 2. Metrics to Add

**In `packages/core/metrics.py`:**

```python
# UI interaction metrics
ui_flatten_clicks_total = Counter('ui_flatten_clicks_total', 'Total flatten button clicks')
ui_flatten_confirms_total = Counter('ui_flatten_confirms_total', 'Total flatten confirmations')

# Flatten request metrics
flatten_requests_total = Counter(
    'flatten_requests_total',
    'Total flatten requests',
    ['result']  # result: ok, error, rate_limited
)

# Already exists, but ensure it's exported:
# flatten_duration_seconds (Histogram)
# api_req_inflight (Gauge with route label)
```

### 3. Audit Logging

**Create `packages/core/audit.py`:**

```python
"""Structured audit logging for security events"""
import json
import structlog
from datetime import datetime

audit_log = structlog.get_logger("audit")

def log_flatten_attempt(
    ip: str,
    req_id: str,
    mode: str,
    positions_before: int,
    positions_after: int,
    duration_ms: int,
    result: str,
    user_agent: str = "unknown",
):
    """Log flatten attempt as structured JSON"""
    audit_log.info(
        "flatten_attempt",
        ts=datetime.utcnow().isoformat(),
        actor="web",
        ip=ip,
        route="/flatten",
        mode=mode,
        positions_before=positions_before,
        positions_after=positions_after,
        duration_ms=duration_ms,
        result=result,
        req_id=req_id,
        user_agent=user_agent,
    )
```

---

## Environment Variables

**Add to API `.env`:**
```bash
# Flatten security
OPS_KEY=your-shared-secret-key-here
OPS_PIN=optional-4-digit-pin

# Audit
AUDIT_LOG_FILE=logs/audit.jsonl
```

---

## Testing

**Test rate limiting:**
```bash
# Should succeed
curl -X POST http://localhost:8000/flatten \
  -H "X-Ops-Key: $OPS_KEY" \
  -H "X-Request-ID: test-1"

# Should fail (rate limited)
curl -X POST http://localhost:8000/flatten \
  -H "X-Ops-Key: $OPS_KEY" \
  -H "X-Request-ID: test-2"
```

**Test lockout:**
```bash
# 3 failed attempts → 60s lockout
for i in {1..3}; do
  curl -X POST http://localhost:8000/flatten \
    -H "X-Ops-Key: wrong-key" \
    -H "X-Request-ID: test-$i"
done

# Should fail (locked out)
curl -X POST http://localhost:8000/flatten \
  -H "X-Ops-Key: $OPS_KEY" \
  -H "X-Request-ID: test-4"
```



