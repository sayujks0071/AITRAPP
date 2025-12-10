# Go-Live Checklist (5 mins)

## Pre-Deployment

### 1. Backend Reachability

```bash
# Test health endpoint
curl -fsS http://<api-host>:8000/health | jq

# Test metrics endpoint  
curl -fsS http://<api-host>:8000/metrics | head -20
```

**Expected:**
- `/health` returns JSON: `{"status": "healthy", "mode": "PAPER", ...}`
- `/metrics` returns Prometheus text format

### 2. Point UI at API

Create `apps/ops-browser/.env.local`:

```bash
# Production
NEXT_PUBLIC_API_BASE=https://ops-api.example.com

# Local development
# NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 3. CORS Configuration

If API and UI are on different origins, configure CORS on API:

**FastAPI example:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ops-ui.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### 4. TLS

- ✅ Use HTTPS for both UI and API
- ✅ Self-signed certs OK on LAN (add to trust store)
- ✅ Production: Use Let's Encrypt or trusted CA

### 5. Guard /flatten

**Security:**
- ✅ No secrets in browser (only `NEXT_PUBLIC_*` env vars)
- ✅ Put UI behind VPN or reverse-proxy auth
- ✅ Optionally require server-side header (e.g., `X-Ops-Key`)
- ✅ Do auth check in API, not client

---

## Final Smoke Test (90s)

```bash
# 1. UI host reachable
curl -I https://ops-ui.example.com

# 2. UI → API connectivity (from your laptop, same origin as browser)
curl -H "Origin: https://ops-ui.example.com" \
  https://ops-api.example.com/health

# 3. Manual checks:
# - Open UI: Mode badge shows PAPER/LIVE, leader ✅
# - All heartbeats < 5s (green)
# - Press Flatten → confirm → success toast
# - P95 appears if histogram exposed
```

---

## Quick Rollback

If anything looks off:

1. **Close browser tab** (stops user actions)
2. **Disable proxy auth** or drop VPN route
3. **Use API directly** to `POST /flatten` if needed
4. **Roll back UI:**
   - Docker: `docker rollback ops-browser:previous`
   - Vercel: Revert to previous deployment

---

## Features Ready

- ✅ Real-time metrics (1.5s polling)
- ✅ Health monitoring (leader, heartbeats, mode)
- ✅ Positions & Orders tables
- ✅ Emergency Flatten with confirmation
- ✅ Toast notifications (leader loss, heartbeats, orphans)
- ✅ Hotkeys (`f` = Flatten, `r` = Refresh, `?` = Help)
- ✅ Offline detection + stale data indicators
- ✅ Timezone toggle (IST/UTC) with persistence

---

**You're ready to deploy!** See `DEPLOYMENT.md` for detailed deployment options.











