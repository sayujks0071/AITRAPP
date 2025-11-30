# Production CORS Configuration

## Current Setup (Development)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

## Production Hardening

### 1. Set Exact Origins (Not Wildcard)

**Before deployment, update `apps/api/main.py`:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ops-ui.yourdomain.com",
        "https://ops-ui-staging.yourdomain.com",  # If you have staging
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
    allow_headers=["Content-Type", "Authorization", "X-Ops-Key", "X-Request-ID"],
    max_age=600,
)
```

**Why:**
- Wildcard (`*`) doesn't work with `allow_credentials=True`
- Exact origins are more secure
- Prevents unauthorized domains from accessing your API

### 2. Add Vary Header (Optional but Recommended)

For better proxy/CDN behavior, add `Vary: Origin` header:

```python
# FastAPI CORS middleware handles this automatically
# But you can verify with:
curl -i -H 'Origin: https://ops-ui.example.com' http://localhost:8000/health | grep Vary
```

### 3. Credentials and Cookies

If you send cookies/credentials:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ops-ui.yourdomain.com"],  # Must be exact, not *
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Important:** When `allow_credentials=True`, you **cannot** use `allow_origins=["*"]`. You must specify exact origins.

### 4. Preflight (OPTIONS) Handling

FastAPI's CORS middleware automatically handles OPTIONS preflight requests. Verify with:

```bash
make ops-verify-preflight
```

**Expected response:**
```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://ops-ui.yourdomain.com
Access-Control-Allow-Methods: GET,POST,OPTIONS
Access-Control-Allow-Headers: content-type
Access-Control-Max-Age: 600
```

### 5. Cache Control Headers

All endpoints now include cache control headers:

- `/metrics`: `Cache-Control: no-store, no-cache, must-revalidate`
- `/ready`: `Cache-Control: no-store, no-cache, must-revalidate`
- `/health`: Standard headers (can add cache control if needed)

This prevents intermediary caching of real-time metrics.

## Verification Checklist

Before deploying to production:

- [ ] Update `allow_origins` to exact production UI domain(s)
- [ ] Remove wildcard origins (`*`)
- [ ] Test preflight: `make ops-verify-preflight`
- [ ] Test error paths: `make ops-verify-cors`
- [ ] Verify cache control headers on `/metrics`
- [ ] Test from production UI origin (not localhost)
- [ ] Check browser console for CORS errors

## Environment-Based Configuration

For different environments, use environment variables:

```python
import os

ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)
```

Then set in production:
```bash
export CORS_ALLOWED_ORIGINS="https://ops-ui.yourdomain.com"
```











