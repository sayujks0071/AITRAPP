# AITRAPP Trading Ops Browser

Production-ready, real-time trading operations dashboard for monitoring AITRAPP backend.

## Features

- **Real-time Metrics**: Live Prometheus metrics parsing and display
- **Health Monitoring**: System health, leader lock, heartbeats
- **P&L Tracking**: Positions, unrealized P&L, daily performance
- **Order Management**: Active orders, OCO groups, execution status
- **Exchange Metrics**: Crypto venue metrics (Binance rate limits, time skew)
- **Controls**: Emergency flatten, pause/resume (if available)
- **Resilient**: Exponential backoff, offline detection, stale data indicators

## Quick Start

### Development

```bash
cd apps/ops-browser
pnpm install
pnpm dev
```

### Production Smoke Test

```bash
# Set API base URL
echo "NEXT_PUBLIC_API_BASE=https://ops-api.example.com" > .env.local

# Run smoke test
./scripts/prod_smoke.sh
```

## Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **Recharts** (for future charts)
- **Zod** (runtime validation)
- **MSW** (mocking for development)

## Documentation

- **`QUICKSTART.md`** - Quick start guide
- **`DEPLOYMENT.md`** - Production deployment options
- **`GO_LIVE.md`** - Go-live checklist
- **`SECURITY.md`** - Security hardening guide
- **`PROJECT_STRUCTURE.md`** - Code organization
- **`docs/API_ENHANCEMENTS.md`** - Recommended API changes

## Security

See **`SECURITY.md`** for:
- Perimeter security (VPN/proxy auth)
- CORS configuration
- CSP headers
- Flatten endpoint guards
- Rate limiting
- Audit logging

## Production Deployment

See **`DEPLOYMENT.md`** for:
- Go-live checklist
- Docker deployment
- Vercel deployment
- Reverse proxy setup (Caddy)
- Security hardening
- Rollback procedures

## Quality of Life Features

- ✅ **Hotkeys**: `f` = Flatten, `r` = Refresh, `?` = Help
- ✅ **Toast Notifications**: Leader loss, heartbeat warnings, OCO orphans
- ✅ **localStorage Persistence**: Timezone preference saved
- ✅ **Offline Detection**: Banner + last known values
- ✅ **Stale Data Indicators**: 10s threshold

## API Endpoints

The dashboard expects these endpoints from the AITRAPP backend:

### Required

- `GET /metrics` - Prometheus metrics (text/plain)
- `GET /health` - Health check (JSON)
- `GET /ready` - Readiness check (JSON)

### Optional

- `GET /positions` - Open positions (JSON)
- `GET /orders` - Active orders (JSON)
- `GET /state` - System state (JSON)
- `POST /flatten` - Flatten all positions
- `POST /pause` - Pause trading
- `POST /resume` - Resume trading

If optional endpoints are not available, the dashboard will display "Not exposed by server" messages.

## Metrics Parsed

The dashboard parses these Prometheus metrics:

- `trader_is_leader` - Leader lock status
- `trader_marketdata_heartbeat_seconds` - Market data heartbeat
- `trader_order_stream_heartbeat_seconds` - Order stream heartbeat
- `trader_scan_heartbeat_seconds` - Scan loop heartbeat
- `trader_leader_changes_total` - Leader change counter
- `trader_oco_orphans_total` - OCO orphan counter
- `trader_scan_ticks_total` - Total scan cycles
- `trader_binance_used_weight_1m` - Binance rate limit (crypto)
- `trader_binance_order_count_1m` - Binance order count (crypto)
- `trader_binance_time_skew_ms` - Time skew (crypto)
- `crypto_flatten_duration_seconds` - Flatten duration histogram (crypto)

## Status Thresholds

- **Heartbeats**: <5s = green, 5-10s = amber, >10s = red
- **Time Skew**: <1000ms = green, <5000ms = amber, else red
- **Flatten P95**: ≤2s = green, else amber/red
- **Leader Changes**: 0 = green, >0 = amber/red
- **OCO Orphans**: 0 = green, >0 = red

## Mock Mode

Set `NEXT_PUBLIC_API_BASE=/mock` to use MSW mocks.

**Setup MSW:**
```bash
npx msw init public/ --save
```

Then the dashboard will use mock data when `NEXT_PUBLIC_API_BASE=/mock` is set.

## Troubleshooting

See **`TROUBLESHOOTING.md`** for a complete troubleshooting guide.

**Quick fixes:**
- **Stuck on "Loading..."** → Clear MSW service worker (DevTools → Application → Service Workers)
- **CORS errors** → Enable CORS in FastAPI (see `TROUBLESHOOTING.md`)
- **API Offline** → Check API is running: `curl http://localhost:8000/health`
- **Missing metrics** → Trader may not be started (this is OK for smoke test)

### Common Issues

**API Offline:**
- Check `NEXT_PUBLIC_API_BASE` is correct
- Verify backend is running on port 8000
- Check CORS settings on backend
- Dashboard will show "API Offline" banner and use last known values

**Metrics Not Updating:**
- Check browser console for errors
- Verify `/metrics` endpoint returns Prometheus format
- Check network tab for failed requests
- Dashboard uses exponential backoff on errors

**Missing Endpoints:**
- Dashboard gracefully handles missing optional endpoints
- Shows "Not exposed by server" messages
- Core functionality (metrics, health) is required

## Future Enhancements

- SSE/WebSocket support (when API adds `/events`)
- Per-row filters and column pinning
- CSV export
- Mini equity curve charts
- Shortcuts modal (replaces alert)

## License

Same as AITRAPP project.
