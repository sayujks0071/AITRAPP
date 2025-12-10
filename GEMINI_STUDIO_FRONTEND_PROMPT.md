# Gemini Studio Frontend Development Prompt

## Project: AITRAPP Trading Operations Dashboard

Build a modern, real-time trading operations dashboard frontend that connects to a FastAPI backend and integrates Gemini 3 Pro for intelligent trading insights and decision support.

---

## 🎯 Project Overview

**AITRAPP** (Autonomous Intelligent Trading Application) is a sophisticated algorithmic trading system for Indian equity derivatives (NSE/NFO). The frontend should provide real-time visibility into:

- **Live Trading Operations**: Positions, orders, PnL tracking
- **Strategy Performance**: Multi-strategy monitoring with SCANNING/DEPLOYED status
- **Risk Management**: Portfolio heat, margin utilization, guardrails
- **Market Intelligence**: Live indices (NIFTY 50, BANKNIFTY), regime detection
- **AI-Powered Insights**: Using Gemini 3 Pro for trade analysis, risk assessment, and recommendations

---

## 🏗️ Technical Stack Requirements

### Frontend Framework
- **React 18+** with TypeScript
- **Next.js 14+** (App Router) for SSR/SSG capabilities
- **Tailwind CSS** for styling (dark theme preferred)
- **Zustand** or **Jotai** for state management
- **React Query (TanStack Query)** for API data fetching and caching
- **Recharts** or **Chart.js** for data visualization

### AI Integration
- **Google Gemini 3 Pro API** for:
  - Real-time trading analysis
  - Risk assessment explanations
  - Strategy recommendations
  - Natural language queries about portfolio
  - Anomaly detection alerts

### Real-time Updates
- **WebSocket** or **Server-Sent Events (SSE)** for live data streams
- **Polling fallback** for critical metrics (every 1-5 seconds)

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000` (configurable via env)

### Core Endpoints

```
GET  /health                    # System health check
GET  /state                     # Current system state (mode, status)
GET  /api/portfolio/snapshot    # Full portfolio snapshot (Level 13)
GET  /api/strategies/summary    # Strategy performance summary
GET  /api/execution/stats       # Order execution statistics
GET  /api/regime/current        # Current market regime
GET  /api/market/indices        # Live NIFTY 50 & BANKNIFTY prices
GET  /api/positions             # Open positions
GET  /api/orders                # Pending orders
POST /api/control/mode          # Change mode (PAPER/LIVE)
POST /api/control/flatten       # Emergency flatten all positions
GET  /metrics                   # Prometheus metrics (optional)
```

### Response Examples

**Portfolio Snapshot** (`/api/portfolio/snapshot`):
```json
{
  "funds": {
    "net": 1000000.0,
    "available_cash": 850000.0,
    "used_margin": 150000.0,
    "utilisation_pct": 15.0
  },
  "positions": [
    {
      "instrument": "NFO:NIFTY24112225000CE",
      "qty": 25,
      "pnl": 1250.50,
      "strategy": "IntradayShortStrangleV1",
      "avg_price": 245.0,
      "ltp": 295.0
    }
  ],
  "indices": {
    "NIFTY 50": {
      "ltp": 26131.00,
      "change": 125.50,
      "change_pct": 0.48
    },
    "BANKNIFTY": {
      "ltp": 58234.00,
      "change": -234.00,
      "change_pct": -0.40
    }
  },
  "broker_positions_count": 5,
  "algo_positions_count": 3,
  "drift_count": 0
}
```

**Strategy Summary** (`/api/strategies/summary`):
```json
{
  "strategies": [
    {
      "name": "IntradayShortStrangleV1",
      "enabled": true,
      "realised_pnl": 5000.0,
      "unrealised_pnl": 1250.50,
      "hit_rate_20d": 0.65,
      "max_dd_60d": -2500.0,
      "current_allocation_pct": 0.15,
      "role": "Intraday Premium Collection"
    }
  ]
}
```

---

## 🎨 UI/UX Requirements

### Design System
- **Theme**: Dark mode (zinc/gray palette)
- **Typography**: Monospace font for numbers (JetBrains Mono), sans-serif for UI
- **Color Coding**:
  - Green: Profits, positive metrics
  - Red: Losses, alerts, critical
  - Blue: SCANNING status, neutral info
  - Purple: DEPLOYED strategies, active
  - Amber: Warnings, drift detection

### Key Pages/Components

#### 1. **Dashboard (Main View)**
- **Top Bar**: Live indices (NIFTY 50, BANKNIFTY) with real-time prices
- **System Status**: Mode badge (LIVE/PAPER), Leader status, heartbeat indicators
- **Portfolio Summary Card**:
  - Net Liquid: ₹X,XXX,XXX
  - Available Cash: ₹X,XXX,XXX
  - Used Margin: ₹X,XXX,XXX (with utilization %)
  - Daily PnL: ₹X,XXX (color-coded)
- **Strategy Grid**: Cards showing:
  - Strategy name and role
  - Status: SCANNING (blue radar animation) or DEPLOYED (purple badge)
  - Total PnL (realized + unrealized)
  - Hit rate, Max DD, Allocation %
  - Visual progress bar for allocation
- **Positions Table**: 
  - Instrument, Quantity, PnL, Strategy Tag (ALGO/MANUAL)
  - Sortable, filterable
  - Color-coded PnL
- **Orders Table**: Pending orders with status, fill progress

#### 2. **AI Insights Panel** (Gemini 3 Pro Integration)
- **Natural Language Query**: "Why did IntradayShortStrangle lose money today?"
- **Risk Analysis**: AI-generated explanation of current portfolio risk
- **Strategy Recommendations**: AI suggestions based on market regime
- **Anomaly Detection**: AI alerts for unusual patterns
- **Chat Interface**: Conversational AI assistant for trading questions

#### 3. **Strategy Detail View**
- Individual strategy deep-dive:
  - Performance charts (PnL over time)
  - Trade history
  - Current positions
  - AI-generated analysis using Gemini 3 Pro

#### 4. **Risk Monitor**
- Portfolio heat visualization
- Margin utilization gauge
- Guardrail status (per-trade risk, daily loss limit, etc.)
- Drift detection alerts

#### 5. **Control Panel**
- Mode switching (PAPER ↔ LIVE) with confirmation
- Emergency flatten button (with reason input)
- System controls (pause/resume)

---

## 🤖 Gemini 3 Pro Integration

### Use Cases

1. **Portfolio Analysis**
   - Send current portfolio snapshot to Gemini
   - Prompt: "Analyze this portfolio and identify the top 3 risks"
   - Display AI insights in a dedicated panel

2. **Strategy Explanation**
   - User clicks on strategy → Gemini explains strategy logic
   - Prompt: "Explain how IntradayShortStrangleV1 works and when it's most effective"

3. **Trade Recommendations**
   - Based on current market regime and portfolio state
   - Prompt: "Given current NIFTY volatility and my positions, what adjustments should I consider?"

4. **Natural Language Queries**
   - Chat interface: "What's my exposure to NIFTY 25000 strike?"
   - "Why is my PnL negative today?"
   - "Should I flatten my positions before market close?"

5. **Anomaly Detection**
   - Periodically send metrics to Gemini
   - Prompt: "Review these trading metrics and flag any anomalies or concerning patterns"

### Implementation Pattern

```typescript
// Example: Gemini integration hook
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.NEXT_PUBLIC_GEMINI_API_KEY!);

async function getGeminiInsight(prompt: string, context: any) {
  const model = genAI.getGenerativeModel({ model: 'gemini-3-pro' });
  
  const fullPrompt = `
    You are a trading operations analyst for AITRAPP.
    Current context: ${JSON.stringify(context, null, 2)}
    
    User question: ${prompt}
    
    Provide a concise, actionable analysis.
  `;
  
  const result = await model.generateContent(fullPrompt);
  return result.response.text();
}
```

---

## 📊 Real-time Data Requirements

### Update Frequencies
- **Indices**: Every 1 second
- **Portfolio Snapshot**: Every 5 seconds
- **Strategy Summary**: Every 10 seconds
- **Orders**: Every 2 seconds (when active)
- **Positions**: Every 5 seconds

### WebSocket Events (if available)
```typescript
// Preferred: WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'position_update':
      updatePositions(data.payload);
      break;
    case 'order_fill':
      showNotification('Order filled', data.payload);
      break;
    case 'regime_change':
      showAlert('Market regime changed', data.payload);
      break;
  }
};
```

### Fallback: Polling
```typescript
// Use React Query with short intervals
useQuery({
  queryKey: ['portfolio'],
  queryFn: fetchPortfolio,
  refetchInterval: 5000, // 5 seconds
});
```

---

## 🎯 Key Features to Implement

### 1. **Mission Control Dashboard**
- Real-time market data display
- Strategy status indicators (SCANNING vs DEPLOYED)
- Portfolio reconciliation (ALGO vs MANUAL tags)
- Live PnL tracking

### 2. **AI-Powered Insights**
- Gemini 3 Pro chat interface
- Contextual analysis based on current portfolio
- Risk assessment explanations
- Strategy recommendations

### 3. **Risk Visualization**
- Portfolio heat maps
- Margin utilization gauges
- Guardrail status indicators
- Drift detection alerts

### 4. **Control Actions**
- Mode switching with confirmation
- Emergency flatten with reason logging
- Strategy enable/disable toggles

### 5. **Performance Analytics**
- Strategy performance charts
- Trade history with filters
- PnL attribution analysis

---

## 🔒 Security Considerations

- **API Key Management**: Store Gemini API key in environment variables
- **CORS**: Backend already configured for `localhost:3000`
- **Rate Limiting**: Implement client-side rate limiting for Gemini calls
- **Error Handling**: Graceful degradation if Gemini API is unavailable

---

## 📦 Project Structure

```
apps/ops-browser-gemini/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Main dashboard
│   ├── strategies/
│   │   └── [name]/page.tsx   # Strategy detail
│   └── api/
│       └── gemini/
│           └── route.ts      # Gemini API proxy
├── components/
│   ├── dashboard/
│   │   ├── PortfolioCard.tsx
│   │   ├── StrategyGrid.tsx
│   │   ├── PositionsTable.tsx
│   │   └── OrdersTable.tsx
│   ├── ai/
│   │   ├── GeminiChat.tsx
│   │   ├── InsightPanel.tsx
│   │   └── RiskAnalysis.tsx
│   └── ui/                   # shadcn/ui components
├── hooks/
│   ├── usePortfolio.ts
│   ├── useStrategies.ts
│   ├── useGemini.ts
│   └── useWebSocket.ts
├── lib/
│   ├── api.ts                # API client
│   └── gemini.ts             # Gemini integration
└── types/
    └── index.ts              # TypeScript types
```

---

## 🚀 Getting Started Instructions

1. **Initialize Next.js project**:
   ```bash
   npx create-next-app@latest ops-browser-gemini --typescript --tailwind --app
   ```

2. **Install dependencies**:
   ```bash
   npm install @google/generative-ai @tanstack/react-query zustand recharts
   ```

3. **Set environment variables**:
   ```env
   NEXT_PUBLIC_API_BASE=http://localhost:8000
   NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Implement API client** with React Query for data fetching

5. **Build dashboard components** following the design system

6. **Integrate Gemini 3 Pro** for AI insights

7. **Add real-time updates** via WebSocket or polling

---

## ✅ Success Criteria

- ✅ Real-time dashboard showing live trading data
- ✅ Strategy status correctly displays SCANNING/DEPLOYED
- ✅ Portfolio positions tagged as ALGO/MANUAL
- ✅ Gemini 3 Pro provides contextual insights
- ✅ Natural language queries work for portfolio analysis
- ✅ Responsive design works on desktop and tablet
- ✅ Error handling for API failures
- ✅ Smooth real-time updates without flickering

---

## 🎨 Design Inspiration

Reference the existing `web_dashboard.html` for:
- Dark theme color scheme
- Strategy card layouts
- Status indicators (SCANNING radar animation, DEPLOYED badges)
- Portfolio table styling
- Typography choices

Enhance with:
- Modern React component patterns
- Better state management
- AI chat interface
- More interactive visualizations

---

## 📝 Additional Notes

- The backend is already running and tested
- CORS is configured for `localhost:3000`
- All API endpoints are documented and working
- Focus on creating a polished, production-ready UI
- Gemini integration should feel natural and helpful, not intrusive
- Prioritize real-time updates for critical trading data

---

**Ready to build!** Start with the main dashboard, then add Gemini integration, then enhance with advanced features.




## Project: AITRAPP Trading Operations Dashboard

Build a modern, real-time trading operations dashboard frontend that connects to a FastAPI backend and integrates Gemini 3 Pro for intelligent trading insights and decision support.

---

## 🎯 Project Overview

**AITRAPP** (Autonomous Intelligent Trading Application) is a sophisticated algorithmic trading system for Indian equity derivatives (NSE/NFO). The frontend should provide real-time visibility into:

- **Live Trading Operations**: Positions, orders, PnL tracking
- **Strategy Performance**: Multi-strategy monitoring with SCANNING/DEPLOYED status
- **Risk Management**: Portfolio heat, margin utilization, guardrails
- **Market Intelligence**: Live indices (NIFTY 50, BANKNIFTY), regime detection
- **AI-Powered Insights**: Using Gemini 3 Pro for trade analysis, risk assessment, and recommendations

---

## 🏗️ Technical Stack Requirements

### Frontend Framework
- **React 18+** with TypeScript
- **Next.js 14+** (App Router) for SSR/SSG capabilities
- **Tailwind CSS** for styling (dark theme preferred)
- **Zustand** or **Jotai** for state management
- **React Query (TanStack Query)** for API data fetching and caching
- **Recharts** or **Chart.js** for data visualization

### AI Integration
- **Google Gemini 3 Pro API** for:
  - Real-time trading analysis
  - Risk assessment explanations
  - Strategy recommendations
  - Natural language queries about portfolio
  - Anomaly detection alerts

### Real-time Updates
- **WebSocket** or **Server-Sent Events (SSE)** for live data streams
- **Polling fallback** for critical metrics (every 1-5 seconds)

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000` (configurable via env)

### Core Endpoints

```
GET  /health                    # System health check
GET  /state                     # Current system state (mode, status)
GET  /api/portfolio/snapshot    # Full portfolio snapshot (Level 13)
GET  /api/strategies/summary    # Strategy performance summary
GET  /api/execution/stats       # Order execution statistics
GET  /api/regime/current        # Current market regime
GET  /api/market/indices        # Live NIFTY 50 & BANKNIFTY prices
GET  /api/positions             # Open positions
GET  /api/orders                # Pending orders
POST /api/control/mode          # Change mode (PAPER/LIVE)
POST /api/control/flatten       # Emergency flatten all positions
GET  /metrics                   # Prometheus metrics (optional)
```

### Response Examples

**Portfolio Snapshot** (`/api/portfolio/snapshot`):
```json
{
  "funds": {
    "net": 1000000.0,
    "available_cash": 850000.0,
    "used_margin": 150000.0,
    "utilisation_pct": 15.0
  },
  "positions": [
    {
      "instrument": "NFO:NIFTY24112225000CE",
      "qty": 25,
      "pnl": 1250.50,
      "strategy": "IntradayShortStrangleV1",
      "avg_price": 245.0,
      "ltp": 295.0
    }
  ],
  "indices": {
    "NIFTY 50": {
      "ltp": 26131.00,
      "change": 125.50,
      "change_pct": 0.48
    },
    "BANKNIFTY": {
      "ltp": 58234.00,
      "change": -234.00,
      "change_pct": -0.40
    }
  },
  "broker_positions_count": 5,
  "algo_positions_count": 3,
  "drift_count": 0
}
```

**Strategy Summary** (`/api/strategies/summary`):
```json
{
  "strategies": [
    {
      "name": "IntradayShortStrangleV1",
      "enabled": true,
      "realised_pnl": 5000.0,
      "unrealised_pnl": 1250.50,
      "hit_rate_20d": 0.65,
      "max_dd_60d": -2500.0,
      "current_allocation_pct": 0.15,
      "role": "Intraday Premium Collection"
    }
  ]
}
```

---

## 🎨 UI/UX Requirements

### Design System
- **Theme**: Dark mode (zinc/gray palette)
- **Typography**: Monospace font for numbers (JetBrains Mono), sans-serif for UI
- **Color Coding**:
  - Green: Profits, positive metrics
  - Red: Losses, alerts, critical
  - Blue: SCANNING status, neutral info
  - Purple: DEPLOYED strategies, active
  - Amber: Warnings, drift detection

### Key Pages/Components

#### 1. **Dashboard (Main View)**
- **Top Bar**: Live indices (NIFTY 50, BANKNIFTY) with real-time prices
- **System Status**: Mode badge (LIVE/PAPER), Leader status, heartbeat indicators
- **Portfolio Summary Card**:
  - Net Liquid: ₹X,XXX,XXX
  - Available Cash: ₹X,XXX,XXX
  - Used Margin: ₹X,XXX,XXX (with utilization %)
  - Daily PnL: ₹X,XXX (color-coded)
- **Strategy Grid**: Cards showing:
  - Strategy name and role
  - Status: SCANNING (blue radar animation) or DEPLOYED (purple badge)
  - Total PnL (realized + unrealized)
  - Hit rate, Max DD, Allocation %
  - Visual progress bar for allocation
- **Positions Table**: 
  - Instrument, Quantity, PnL, Strategy Tag (ALGO/MANUAL)
  - Sortable, filterable
  - Color-coded PnL
- **Orders Table**: Pending orders with status, fill progress

#### 2. **AI Insights Panel** (Gemini 3 Pro Integration)
- **Natural Language Query**: "Why did IntradayShortStrangle lose money today?"
- **Risk Analysis**: AI-generated explanation of current portfolio risk
- **Strategy Recommendations**: AI suggestions based on market regime
- **Anomaly Detection**: AI alerts for unusual patterns
- **Chat Interface**: Conversational AI assistant for trading questions

#### 3. **Strategy Detail View**
- Individual strategy deep-dive:
  - Performance charts (PnL over time)
  - Trade history
  - Current positions
  - AI-generated analysis using Gemini 3 Pro

#### 4. **Risk Monitor**
- Portfolio heat visualization
- Margin utilization gauge
- Guardrail status (per-trade risk, daily loss limit, etc.)
- Drift detection alerts

#### 5. **Control Panel**
- Mode switching (PAPER ↔ LIVE) with confirmation
- Emergency flatten button (with reason input)
- System controls (pause/resume)

---

## 🤖 Gemini 3 Pro Integration

### Use Cases

1. **Portfolio Analysis**
   - Send current portfolio snapshot to Gemini
   - Prompt: "Analyze this portfolio and identify the top 3 risks"
   - Display AI insights in a dedicated panel

2. **Strategy Explanation**
   - User clicks on strategy → Gemini explains strategy logic
   - Prompt: "Explain how IntradayShortStrangleV1 works and when it's most effective"

3. **Trade Recommendations**
   - Based on current market regime and portfolio state
   - Prompt: "Given current NIFTY volatility and my positions, what adjustments should I consider?"

4. **Natural Language Queries**
   - Chat interface: "What's my exposure to NIFTY 25000 strike?"
   - "Why is my PnL negative today?"
   - "Should I flatten my positions before market close?"

5. **Anomaly Detection**
   - Periodically send metrics to Gemini
   - Prompt: "Review these trading metrics and flag any anomalies or concerning patterns"

### Implementation Pattern

```typescript
// Example: Gemini integration hook
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.NEXT_PUBLIC_GEMINI_API_KEY!);

async function getGeminiInsight(prompt: string, context: any) {
  const model = genAI.getGenerativeModel({ model: 'gemini-3-pro' });
  
  const fullPrompt = `
    You are a trading operations analyst for AITRAPP.
    Current context: ${JSON.stringify(context, null, 2)}
    
    User question: ${prompt}
    
    Provide a concise, actionable analysis.
  `;
  
  const result = await model.generateContent(fullPrompt);
  return result.response.text();
}
```

---

## 📊 Real-time Data Requirements

### Update Frequencies
- **Indices**: Every 1 second
- **Portfolio Snapshot**: Every 5 seconds
- **Strategy Summary**: Every 10 seconds
- **Orders**: Every 2 seconds (when active)
- **Positions**: Every 5 seconds

### WebSocket Events (if available)
```typescript
// Preferred: WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'position_update':
      updatePositions(data.payload);
      break;
    case 'order_fill':
      showNotification('Order filled', data.payload);
      break;
    case 'regime_change':
      showAlert('Market regime changed', data.payload);
      break;
  }
};
```

### Fallback: Polling
```typescript
// Use React Query with short intervals
useQuery({
  queryKey: ['portfolio'],
  queryFn: fetchPortfolio,
  refetchInterval: 5000, // 5 seconds
});
```

---

## 🎯 Key Features to Implement

### 1. **Mission Control Dashboard**
- Real-time market data display
- Strategy status indicators (SCANNING vs DEPLOYED)
- Portfolio reconciliation (ALGO vs MANUAL tags)
- Live PnL tracking

### 2. **AI-Powered Insights**
- Gemini 3 Pro chat interface
- Contextual analysis based on current portfolio
- Risk assessment explanations
- Strategy recommendations

### 3. **Risk Visualization**
- Portfolio heat maps
- Margin utilization gauges
- Guardrail status indicators
- Drift detection alerts

### 4. **Control Actions**
- Mode switching with confirmation
- Emergency flatten with reason logging
- Strategy enable/disable toggles

### 5. **Performance Analytics**
- Strategy performance charts
- Trade history with filters
- PnL attribution analysis

---

## 🔒 Security Considerations

- **API Key Management**: Store Gemini API key in environment variables
- **CORS**: Backend already configured for `localhost:3000`
- **Rate Limiting**: Implement client-side rate limiting for Gemini calls
- **Error Handling**: Graceful degradation if Gemini API is unavailable

---

## 📦 Project Structure

```
apps/ops-browser-gemini/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Main dashboard
│   ├── strategies/
│   │   └── [name]/page.tsx   # Strategy detail
│   └── api/
│       └── gemini/
│           └── route.ts      # Gemini API proxy
├── components/
│   ├── dashboard/
│   │   ├── PortfolioCard.tsx
│   │   ├── StrategyGrid.tsx
│   │   ├── PositionsTable.tsx
│   │   └── OrdersTable.tsx
│   ├── ai/
│   │   ├── GeminiChat.tsx
│   │   ├── InsightPanel.tsx
│   │   └── RiskAnalysis.tsx
│   └── ui/                   # shadcn/ui components
├── hooks/
│   ├── usePortfolio.ts
│   ├── useStrategies.ts
│   ├── useGemini.ts
│   └── useWebSocket.ts
├── lib/
│   ├── api.ts                # API client
│   └── gemini.ts             # Gemini integration
└── types/
    └── index.ts              # TypeScript types
```

---

## 🚀 Getting Started Instructions

1. **Initialize Next.js project**:
   ```bash
   npx create-next-app@latest ops-browser-gemini --typescript --tailwind --app
   ```

2. **Install dependencies**:
   ```bash
   npm install @google/generative-ai @tanstack/react-query zustand recharts
   ```

3. **Set environment variables**:
   ```env
   NEXT_PUBLIC_API_BASE=http://localhost:8000
   NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Implement API client** with React Query for data fetching

5. **Build dashboard components** following the design system

6. **Integrate Gemini 3 Pro** for AI insights

7. **Add real-time updates** via WebSocket or polling

---

## ✅ Success Criteria

- ✅ Real-time dashboard showing live trading data
- ✅ Strategy status correctly displays SCANNING/DEPLOYED
- ✅ Portfolio positions tagged as ALGO/MANUAL
- ✅ Gemini 3 Pro provides contextual insights
- ✅ Natural language queries work for portfolio analysis
- ✅ Responsive design works on desktop and tablet
- ✅ Error handling for API failures
- ✅ Smooth real-time updates without flickering

---

## 🎨 Design Inspiration

Reference the existing `web_dashboard.html` for:
- Dark theme color scheme
- Strategy card layouts
- Status indicators (SCANNING radar animation, DEPLOYED badges)
- Portfolio table styling
- Typography choices

Enhance with:
- Modern React component patterns
- Better state management
- AI chat interface
- More interactive visualizations

---

## 📝 Additional Notes

- The backend is already running and tested
- CORS is configured for `localhost:3000`
- All API endpoints are documented and working
- Focus on creating a polished, production-ready UI
- Gemini integration should feel natural and helpful, not intrusive
- Prioritize real-time updates for critical trading data

---

**Ready to build!** Start with the main dashboard, then add Gemini integration, then enhance with advanced features.





