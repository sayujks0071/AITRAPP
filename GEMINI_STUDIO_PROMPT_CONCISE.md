# Gemini Studio Prompt (Copy-Paste Ready)

```
Build a real-time trading operations dashboard for AITRAPP (Autonomous Intelligent Trading Application) using Next.js 14, TypeScript, Tailwind CSS, and integrate Google Gemini 3 Pro for AI-powered trading insights.

## Tech Stack
- Next.js 14+ (App Router) with TypeScript
- Tailwind CSS (dark theme: zinc/gray palette)
- React Query (TanStack Query) for API data fetching
- Zustand for state management
- Recharts for visualizations
- Google Gemini 3 Pro API for AI insights
- WebSocket or polling for real-time updates

## API Base URL
http://localhost:8000

## Key Endpoints
- GET /health - System health
- GET /state - System state (mode, status)
- GET /api/portfolio/snapshot - Portfolio with positions, funds, indices
- GET /api/strategies/summary - Strategy performance
- GET /api/execution/stats - Order execution stats
- GET /api/regime/current - Market regime
- GET /api/market/indices - Live NIFTY 50 & BANKNIFTY
- GET /api/positions - Open positions
- GET /api/orders - Pending orders
- POST /api/control/mode - Change mode (PAPER/LIVE)
- POST /api/control/flatten - Emergency flatten

## Dashboard Requirements

### Main Dashboard Page
1. **Top Bar**: Live NIFTY 50 and BANKNIFTY prices (update every 1s)
2. **System Status**: Mode badge (LIVE/PAPER), Leader status, heartbeat
3. **Portfolio Summary Card**:
   - Net Liquid, Available Cash, Used Margin, Daily PnL
   - Color-coded: green (profit), red (loss)
4. **Strategy Grid**: Cards showing:
   - Strategy name, role
   - Status: "SCANNING" (blue radar animation) or "DEPLOYED" (purple badge)
   - Total PnL, Hit Rate, Max DD, Allocation %
   - Visual progress bar
5. **Positions Table**: Instrument, Qty, PnL, Strategy Tag (ALGO/MANUAL)
6. **Orders Table**: Pending orders with status

### Gemini 3 Pro Integration
Create an AI Insights Panel with:
- Natural language chat: "Why did my strategy lose money?"
- Portfolio risk analysis: AI explains current risk factors
- Strategy recommendations: Based on market regime
- Anomaly detection: AI flags unusual patterns
- Context-aware responses using current portfolio data

Example Gemini prompt structure:
```
You are a trading operations analyst for AITRAPP.
Current portfolio context: {portfolio_snapshot}
User question: {user_query}
Provide concise, actionable analysis.
```

### Real-time Updates
- Indices: 1s interval
- Portfolio: 5s interval
- Strategies: 10s interval
- Orders: 2s interval (when active)

### Design System
- Dark theme (background: #09090b, cards: rgba(24,24,27,0.6))
- Colors: Green (profit), Red (loss/alerts), Blue (scanning), Purple (deployed), Amber (warnings)
- Typography: JetBrains Mono for numbers, sans-serif for UI
- Glass-morphism panels with backdrop blur

### Key Features
1. Real-time data updates without flickering
2. Strategy status: SCANNING (no positions) vs DEPLOYED (has positions)
3. Portfolio reconciliation: ALGO vs MANUAL position tags
4. AI chat interface for trading questions
5. Risk visualization: Portfolio heat, margin utilization
6. Control panel: Mode switching, emergency flatten

## Project Structure
```
app/
├── page.tsx              # Main dashboard
├── strategies/[name]/    # Strategy detail
└── api/gemini/route.ts   # Gemini API proxy
components/
├── dashboard/            # Portfolio, Strategy, Positions, Orders
├── ai/                   # GeminiChat, InsightPanel
└── ui/                   # shadcn/ui components
hooks/
├── usePortfolio.ts
├── useStrategies.ts
├── useGemini.ts
└── useWebSocket.ts
```

## Environment Variables
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_key_here

## Success Criteria
✅ Real-time dashboard with live trading data
✅ Strategy SCANNING/DEPLOYED status working
✅ ALGO/MANUAL position tags displayed
✅ Gemini 3 Pro provides contextual insights
✅ Natural language queries work
✅ Responsive design
✅ Smooth real-time updates

Start by building the main dashboard page, then add Gemini integration, then enhance with advanced features. Use React Query for data fetching with appropriate refetch intervals. Implement error boundaries and loading states.
```




```
Build a real-time trading operations dashboard for AITRAPP (Autonomous Intelligent Trading Application) using Next.js 14, TypeScript, Tailwind CSS, and integrate Google Gemini 3 Pro for AI-powered trading insights.

## Tech Stack
- Next.js 14+ (App Router) with TypeScript
- Tailwind CSS (dark theme: zinc/gray palette)
- React Query (TanStack Query) for API data fetching
- Zustand for state management
- Recharts for visualizations
- Google Gemini 3 Pro API for AI insights
- WebSocket or polling for real-time updates

## API Base URL
http://localhost:8000

## Key Endpoints
- GET /health - System health
- GET /state - System state (mode, status)
- GET /api/portfolio/snapshot - Portfolio with positions, funds, indices
- GET /api/strategies/summary - Strategy performance
- GET /api/execution/stats - Order execution stats
- GET /api/regime/current - Market regime
- GET /api/market/indices - Live NIFTY 50 & BANKNIFTY
- GET /api/positions - Open positions
- GET /api/orders - Pending orders
- POST /api/control/mode - Change mode (PAPER/LIVE)
- POST /api/control/flatten - Emergency flatten

## Dashboard Requirements

### Main Dashboard Page
1. **Top Bar**: Live NIFTY 50 and BANKNIFTY prices (update every 1s)
2. **System Status**: Mode badge (LIVE/PAPER), Leader status, heartbeat
3. **Portfolio Summary Card**:
   - Net Liquid, Available Cash, Used Margin, Daily PnL
   - Color-coded: green (profit), red (loss)
4. **Strategy Grid**: Cards showing:
   - Strategy name, role
   - Status: "SCANNING" (blue radar animation) or "DEPLOYED" (purple badge)
   - Total PnL, Hit Rate, Max DD, Allocation %
   - Visual progress bar
5. **Positions Table**: Instrument, Qty, PnL, Strategy Tag (ALGO/MANUAL)
6. **Orders Table**: Pending orders with status

### Gemini 3 Pro Integration
Create an AI Insights Panel with:
- Natural language chat: "Why did my strategy lose money?"
- Portfolio risk analysis: AI explains current risk factors
- Strategy recommendations: Based on market regime
- Anomaly detection: AI flags unusual patterns
- Context-aware responses using current portfolio data

Example Gemini prompt structure:
```
You are a trading operations analyst for AITRAPP.
Current portfolio context: {portfolio_snapshot}
User question: {user_query}
Provide concise, actionable analysis.
```

### Real-time Updates
- Indices: 1s interval
- Portfolio: 5s interval
- Strategies: 10s interval
- Orders: 2s interval (when active)

### Design System
- Dark theme (background: #09090b, cards: rgba(24,24,27,0.6))
- Colors: Green (profit), Red (loss/alerts), Blue (scanning), Purple (deployed), Amber (warnings)
- Typography: JetBrains Mono for numbers, sans-serif for UI
- Glass-morphism panels with backdrop blur

### Key Features
1. Real-time data updates without flickering
2. Strategy status: SCANNING (no positions) vs DEPLOYED (has positions)
3. Portfolio reconciliation: ALGO vs MANUAL position tags
4. AI chat interface for trading questions
5. Risk visualization: Portfolio heat, margin utilization
6. Control panel: Mode switching, emergency flatten

## Project Structure
```
app/
├── page.tsx              # Main dashboard
├── strategies/[name]/    # Strategy detail
└── api/gemini/route.ts   # Gemini API proxy
components/
├── dashboard/            # Portfolio, Strategy, Positions, Orders
├── ai/                   # GeminiChat, InsightPanel
└── ui/                   # shadcn/ui components
hooks/
├── usePortfolio.ts
├── useStrategies.ts
├── useGemini.ts
└── useWebSocket.ts
```

## Environment Variables
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_key_here

## Success Criteria
✅ Real-time dashboard with live trading data
✅ Strategy SCANNING/DEPLOYED status working
✅ ALGO/MANUAL position tags displayed
✅ Gemini 3 Pro provides contextual insights
✅ Natural language queries work
✅ Responsive design
✅ Smooth real-time updates

Start by building the main dashboard page, then add Gemini integration, then enhance with advanced features. Use React Query for data fetching with appropriate refetch intervals. Implement error boundaries and loading states.
```





