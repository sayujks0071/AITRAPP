# Security Hardening Guide

## Perimeter Security

### 1. Authentication

**VPN or Reverse-Proxy Auth:**
- Put UI behind VPN (recommended for internal ops)
- Or use reverse-proxy Basic Auth/OIDC
- **Never** put tokens in the browser

**Example (Caddy Basic Auth):**
```caddy
ops-ui.example.com {
  basicauth /* {
    admin JDJhJDEwJE5Y...   # caddy hash-password
  }
  reverse_proxy 127.0.0.1:3000
}
```

### 2. CORS Configuration

**Pin to exact UI origin:**
```python
# FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ops-ui.example.com"],  # Exact match, no wildcards
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Ops-Key", "X-Request-ID"],
)
```

### 3. TLS + HSTS

**Enforce HTTPS:**
- Use TLS 1.2+ for both UI and API
- Enable HSTS headers
- Self-signed certs OK on LAN (add to trust store)
- Production: Use Let's Encrypt or trusted CA

---

## Browser Defenses

### Content Security Policy (CSP)

**Next.js middleware (`middleware.ts`):**
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  
  // CSP
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; " +
    "connect-src 'self' https://ops-api.example.com; " +
    "img-src 'self' data:; " +
    "script-src 'self'; " +
    "style-src 'self' 'unsafe-inline'; " +  // Tailwind needs unsafe-inline
    "font-src 'self';"
  );
  
  // Security headers
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  
  return response;
}

export const config = {
  matcher: '/:path*',
};
```

---

## Mutations (Flatten) Security

### Server-Side Guard

**API should require:**
1. **Shared secret header** (e.g., `X-Ops-Key`)
2. **Optional ops PIN** in request body
3. **Rate limiting**: 1 flatten per 10s per IP
4. **Lockout**: 3 failures → 60s lockout
5. **Audit logging**: Every attempt (who/when/IP/mode/result)

**Example API guard:**
```python
from fastapi import Header, HTTPException, Request
import time
from collections import defaultdict

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
    client_ip = request.client.host
    
    # Check lockout
    if time.time() < flatten_lockouts.get(client_ip, 0):
        raise HTTPException(429, "Rate limited: too many failed attempts")
    
    # Check header
    if not x_ops_key or x_ops_key != OPS_KEY:
        _record_failed_attempt(client_ip)
        raise HTTPException(403, "Invalid X-Ops-Key")
    
    # Check PIN (optional)
    if OPS_PIN and ops_pin != OPS_PIN:
        _record_failed_attempt(client_ip)
        raise HTTPException(403, "Invalid ops PIN")
    
    # Rate limit: 1 per 10s
    now = time.time()
    attempts = flatten_attempts[client_ip]
    attempts = [t for t in attempts if now - t < 10]
    
    if len(attempts) >= 1:
        raise HTTPException(429, "Rate limited: 1 flatten per 10s")
    
    attempts.append(now)
    flatten_attempts[client_ip] = attempts
    
    # Audit log
    audit_log.info({
        "ts": datetime.utcnow().isoformat(),
        "actor": "web",
        "ip": client_ip,
        "route": "/flatten",
        "mode": settings.app_mode.value,
        "req_id": x_request_id,
        "result": "ok",
    })
    
    # ... flatten logic ...
```

---

## Secrets Management

### ✅ DO:
- Use `NEXT_PUBLIC_*` env vars for harmless values (API base URL)
- Keep secrets server-side only
- Use VPN/proxy auth for UI access
- Rotate `OPS_KEY` regularly

### ❌ DON'T:
- Put API keys in browser
- Commit `.env.local` to git
- Use `NEXT_PUBLIC_*` for secrets
- Trust client-side validation for auth

---

## Observability

### Metrics to Add (API)

```python
# In packages/core/metrics.py
ui_flatten_clicks_total = Counter('ui_flatten_clicks_total')
ui_flatten_confirms_total = Counter('ui_flatten_confirms_total')
flatten_requests_total = Counter('flatten_requests_total', ['result'])
flatten_duration_seconds = Histogram('flatten_duration_seconds')
api_req_inflight = Gauge('api_req_inflight', ['route'])
```

### Audit Log Format

```json
{
  "ts": "2025-11-15T09:31:04Z",
  "actor": "web",
  "ip": "203.0.113.10",
  "route": "/flatten",
  "mode": "PAPER",
  "positions_before": 1,
  "positions_after": 0,
  "duration_ms": 412,
  "result": "ok",
  "req_id": "req_abc123",
  "user_agent": "Mozilla/5.0..."
}
```

### Trace Correlation

**UI generates `X-Request-ID` for POSTs:**
```typescript
// In lib/api.ts
const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

fetch(url, {
  headers: {
    'X-Request-ID': requestId,
    // ...
  }
});
```

**API echoes in logs/metrics:**
```python
req_id = request.headers.get("X-Request-ID", "unknown")
logger.info("Flatten request", req_id=req_id, ...)
```

---

## Quick Wins Checklist

- [ ] UI behind VPN or reverse-proxy auth
- [ ] CORS pinned to exact UI origin
- [ ] TLS + HSTS enabled
- [ ] CSP headers configured
- [ ] `/flatten` requires `X-Ops-Key` header
- [ ] Rate limiting on `/flatten` (1 per 10s)
- [ ] Audit logging for all flatten attempts
- [ ] `X-Request-ID` correlation
- [ ] No secrets in `NEXT_PUBLIC_*` env vars
- [ ] Security headers (CSP, X-Frame-Options, etc.)

---

## Incident Response

**If unauthorized flatten detected:**
1. Immediately disable `OPS_KEY` in API env
2. Check audit logs for source IP
3. Review rate limit violations
4. Rotate all shared secrets
5. Investigate VPN/proxy auth logs






