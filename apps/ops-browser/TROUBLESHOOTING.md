# Troubleshooting Guide

## Quick Checklist

### 1) Verify API is Running

```bash
# Check health endpoint
curl -i http://localhost:8000/health

# Check metrics endpoint
curl -s http://localhost:8000/metrics | head
```

**Expected:**
- `/health` → `200 OK` with JSON response
- `/metrics` → Prometheus text format (e.g., `trader_is_leader`, `trader_*_heartbeat_seconds`)

### 2) Verify UI API Configuration

Create `.env.local` in `apps/ops-browser/`:

```bash
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > apps/ops-browser/.env.local
```

Then restart the dev server:

```bash
cd apps/ops-browser
pnpm dev
```

### 3) Clear Stale MSW Service Worker

**Chrome/Edge:**
1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **Service Workers** in left sidebar
4. Find worker for `localhost:3000`
5. Click **Unregister**

**Or hard refresh:**
- **Mac**: `Cmd+Shift+R`
- **Windows/Linux**: `Ctrl+Shift+R`

### 4) Fix CORS Errors

If you see CORS errors in the browser console, enable CORS in your FastAPI app:

```python
# apps/api/main.py (or wherever FastAPI app is created)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Restart the API** after adding this.

### 5) Dev Flows

**Real API:**
```bash
# Terminal 1: Start API
make paper  # or make crypto-paper

# Terminal 2: Start Dashboard
cd apps/ops-browser
pnpm dev

# Open: http://localhost:3000
```

**Mock Mode:**
```bash
# Set mock mode
echo "NEXT_PUBLIC_API_BASE=/mock" > apps/ops-browser/.env.local

# Start dashboard
cd apps/ops-browser
pnpm dev

# Open: http://localhost:3000
```

### 6) What "Good" Looks Like

✅ **Healthy Dashboard:**
- Mode badge shows `PAPER`/`LIVE` + green leader indicator
- Health tiles all green; heartbeats < 5s
- No "Loading..." overlay
- Tables render (even if empty)
- Toast notifications work

⚠️ **API Offline:**
- Red "API Offline" banner at top
- Last known values displayed
- Retrying with exponential backoff

❌ **Common Issues:**
- Stuck on "Loading..." → Check MSW service worker (step 3)
- CORS errors → Enable CORS in API (step 4)
- "API Offline" banner → Check API is running (step 1)
- Missing metrics → Trader may not be started (this is OK for smoke test)

## Debugging Steps

### Check Browser Console

1. Open DevTools (F12)
2. Go to **Console** tab
3. Look for red errors
4. Share:
   - Error message
   - Stack trace
   - Network request that failed

### Check Network Tab

1. Open DevTools (F12)
2. Go to **Network** tab
3. Refresh page
4. Look for failed requests (red status codes)
5. Check:
   - Request URL
   - Status code (404, 500, CORS error)
   - Response body

### Check API Logs

```bash
# If API is running in terminal, check for errors
# Look for:
# - 500 errors
# - CORS errors
# - Missing endpoints
```

## Common Error Messages

### "API Offline"

**Cause:** API not reachable or not running

**Fix:**
1. Check API is running: `curl http://localhost:8000/health`
2. Verify `NEXT_PUBLIC_API_BASE` in `.env.local`
3. Check firewall/network settings

### CORS Error

**Cause:** API doesn't allow requests from UI origin

**Fix:** Add CORS middleware to FastAPI (see step 4)

### "Loading..." Stuck

**Cause:** MSW service worker blocking or provider issue

**Fix:**
1. Clear service worker (step 3)
2. Hard refresh (Cmd/Ctrl+Shift+R)
3. Check browser console for MSW errors

### Missing Metrics

**Cause:** Trader not started or metrics not initialized

**Fix:** This is OK for smoke test. To fix:
1. Start trader orchestrator
2. Wait for leader lock to be acquired
3. Metrics should appear

### 500 Error on `/ready`

**Cause:** Trader not started or Prometheus gauges not initialized

**Fix:** This is expected if trader isn't running. The dashboard handles this gracefully.

## Still Stuck?

1. **Check browser console** for errors
2. **Check network tab** for failed requests
3. **Check API logs** for server errors
4. **Run smoke test:** `make ops-smoke-no-ui`
5. **Share:**
   - Browser console errors
   - Network request that failed (URL + status)
   - API logs (if available)






