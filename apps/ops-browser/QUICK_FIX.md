# Quick Fix: Dashboard Shows "Last update: Never"

## Symptoms
- Dashboard loads but shows "Last update: Never"
- No health tiles visible
- No metrics updating

## Most Likely Cause: CORS Issue

The browser is blocking the API requests due to CORS.

## Quick Fix

### 1. Check Browser Console
Open DevTools (F12) → Console tab. Look for:
- Red CORS errors
- Failed network requests to `/metrics` or `/health`

### 2. Enable CORS in FastAPI

Add this to your FastAPI app (`apps/api/main.py`):

```python
from fastapi.middleware.cors import CORSMiddleware

# Add this after creating the FastAPI app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Then restart the API:**
```bash
# Stop current API (Ctrl+C)
# Restart it
make paper  # or make crypto-paper
```

### 3. Verify .env.local

Make sure `apps/ops-browser/.env.local` exists:

```bash
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > apps/ops-browser/.env.local
```

**Then restart the dashboard:**
```bash
cd apps/ops-browser
pnpm dev
```

### 4. Hard Refresh Browser

- **Mac**: `Cmd+Shift+R`
- **Windows/Linux**: `Ctrl+Shift+R`

## Expected Result

After fixing CORS:
- ✅ "Last update" shows a timestamp
- ✅ Health tiles appear (heartbeats, leader status)
- ✅ Metrics update every 1.5 seconds
- ✅ Mode badge shows PAPER/LIVE

## Still Not Working?

1. **Check browser console** for specific error messages
2. **Check network tab** (F12 → Network) for failed requests
3. **Verify API is running**: `curl http://localhost:8000/health`
4. **Check API logs** for CORS errors






