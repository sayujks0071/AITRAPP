# Production Deployment Guide

## Go-Live Checklist (5 mins)

### 1. Backend Reachability

```bash
# Test health endpoint
curl -fsS http://<api-host>:8000/health | jq

# Test metrics endpoint
curl -fsS http://<api-host>:8000/metrics | head -20
```

**Expected:**
- `/health` returns JSON with `status`, `mode`, etc.
- `/metrics` returns Prometheus text format

### 2. Point UI at API

Create `apps/ops-browser/.env.local`:

```bash
# Production API
NEXT_PUBLIC_API_BASE=https://ops-api.example.com

# Or local development
# NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 3. CORS Configuration

If API and UI are on different origins, configure CORS on the API:

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

- Use HTTPS for both UI and API
- Self-signed certs are fine on LAN (add to trust store)
- Production: Use Let's Encrypt or trusted CA

### 5. Guard /flatten

**Security:**
- ✅ No secrets in browser (only `NEXT_PUBLIC_*` env vars)
- ✅ Put UI behind VPN or reverse-proxy auth
- ✅ Optionally require server-side header for mutations (e.g., `X-Ops-Key`)
- ✅ Do auth check in API, not client

---

## Deployment Options

### A) Vercel (Fastest)

1. Push app to repo
2. Set project root to `apps/ops-browser`
3. Add env var: `NEXT_PUBLIC_API_BASE=https://ops-api.example.com`
4. Configure CORS on API to allow Vercel domain
5. (Optional) Add Basic Auth via Vercel Middleware

**Vercel Middleware (Basic Auth):**
```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  const auth = authHeader?.replace('Basic ', '');
  
  if (!auth || !isValidAuth(auth)) {
    return new NextResponse('Unauthorized', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="Ops Browser"' },
    });
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
```

### B) Docker (Self-Host)

**Build:**
```bash
docker build -t ops-browser:latest -f apps/ops-browser/Dockerfile .
```

**Run:**
```bash
docker run -d \
  --name ops-browser \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE="https://ops-api.example.com" \
  ops-browser:latest
```

**With docker-compose:**
```yaml
# docker-compose.ops-browser.yml
version: '3.9'
services:
  ops-browser:
    build:
      context: .
      dockerfile: apps/ops-browser/Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE=https://ops-api.example.com
    restart: unless-stopped
```

### C) Reverse Proxy + Basic Auth (Caddy)

**Caddyfile:**
```
ops-ui.example.com {
  basicauth /* {
    admin JDJhJDEwJE5Y...   # bcrypt hash; generate with `caddy hash-password`
  }
  encode zstd gzip
  reverse_proxy 127.0.0.1:3000
}

ops-api.example.com {
  encode zstd gzip
  reverse_proxy 127.0.0.1:8000
  header {
    Access-Control-Allow-Origin https://ops-ui.example.com
    Access-Control-Allow-Methods "GET, POST, OPTIONS"
    Access-Control-Allow-Headers "Content-Type, Authorization"
  }
}
```

**Generate password hash:**
```bash
caddy hash-password
```

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
# - Press Flatten → confirm → success
# - P95 appears if histogram exposed
```

---

## Quick Rollback

If anything looks off after deploy:

1. **Close browser tab** (stops user actions)
2. **Disable proxy auth** or drop VPN route
3. **Use API directly** to `POST /flatten` if needed
4. **Roll back UI:**
   - Docker: `docker rollback ops-browser:previous`
   - Vercel: Revert to previous deployment
   - Manual: Restore previous build/image

---

## Security Checklist

- [ ] UI behind VPN or reverse-proxy auth
- [ ] No secrets in `.env.local` (only `NEXT_PUBLIC_*`)
- [ ] CORS configured on API
- [ ] HTTPS enabled (TLS)
- [ ] `/flatten` endpoint protected (server-side)
- [ ] API rate limiting configured
- [ ] Logs don't expose sensitive data

---

## Monitoring

- **UI Health**: Monitor `/health` endpoint
- **API Connectivity**: Dashboard shows "API Offline" banner
- **Metrics Freshness**: Stale indicator after 10s
- **Error Rate**: Check browser console for failed requests

---

## Troubleshooting

**CORS Errors:**
- Verify `Access-Control-Allow-Origin` includes UI origin
- Check preflight (OPTIONS) requests succeed

**API Offline:**
- Verify API is running and reachable
- Check network connectivity
- Verify `NEXT_PUBLIC_API_BASE` is correct

**Metrics Not Updating:**
- Check `/metrics` endpoint returns Prometheus format
- Verify polling interval (1.5s default)
- Check browser console for errors



