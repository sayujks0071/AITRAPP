# Project Structure

```
apps/ops-browser/
├── app/
│   ├── globals.css          # Tailwind + theme variables
│   ├── layout.tsx           # Root layout with Providers
│   ├── page.tsx             # Main dashboard page
│   └── providers.tsx        # MSW provider (mock mode)
├── components/
│   ├── tiles/               # Health/metric tiles
│   │   ├── HealthTile.tsx
│   │   ├── MetricCard.tsx
│   │   └── ModeBadge.tsx
│   ├── tables/              # Data tables
│   │   ├── PositionsTable.tsx
│   │   └── OrdersTable.tsx
│   └── ui/                  # shadcn/ui components
│       ├── badge.tsx
│       ├── button.tsx
│       ├── card.tsx
│       └── dialog.tsx
├── hooks/                   # Data fetching hooks
│   ├── useMetrics.ts        # Prometheus metrics
│   ├── useHealth.ts         # Health/ready endpoints
│   ├── useFlatten.ts        # Flatten control
│   ├── usePositions.ts      # Positions endpoint
│   └── useOrders.ts         # Orders endpoint
├── lib/                     # Utilities
│   ├── api.ts               # API client functions
│   ├── prom.ts              # Prometheus parser
│   ├── format.ts            # Formatting utilities
│   └── cn.ts                # className utility
├── mocks/                   # MSW mocks
│   ├── handlers.ts          # Mock API handlers
│   └── browser.ts           # MSW browser setup
├── public/                  # Static assets
│   └── mockServiceWorker.js # MSW service worker (generated)
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── postcss.config.js
├── .eslintrc.json
├── .gitignore
├── README.md
└── QUICKSTART.md
```

## Key Files

### Core Dashboard
- `app/page.tsx` - Main dashboard with all tiles, tables, and controls
- `hooks/useMetrics.ts` - Real-time metrics polling with backoff
- `lib/prom.ts` - Prometheus text format parser

### Components
- `components/tiles/HealthTile.tsx` - Status-colored health metrics
- `components/tables/PositionsTable.tsx` - Positions with UPL/RPL
- `components/tables/OrdersTable.tsx` - Orders with OCO groups

### API Integration
- `lib/api.ts` - All API calls (gracefully handles missing endpoints)
- `hooks/useHealth.ts` - Health/ready polling
- `hooks/useFlatten.ts` - Flatten with confirmation dialog

## Data Flow

1. **Metrics**: `useMetrics` → `/metrics` → `parsePrometheusMetrics` → derived health
2. **Health**: `useHealth` → `/health` + `/ready` → mode, status
3. **Positions**: `usePositions` → `/positions` → table display
4. **Orders**: `useOrders` → `/orders` → table display
5. **Controls**: `useFlatten` → `POST /flatten` → confirmation → refresh

## Polling Intervals

- Metrics: 1.5s (with jitter and exponential backoff)
- Health: 10s
- Positions: 5s
- Orders: 3s

## Error Handling

- Exponential backoff on API failures
- Stale data detection (10s threshold)
- Offline banner with last known values
- Graceful degradation for missing endpoints











