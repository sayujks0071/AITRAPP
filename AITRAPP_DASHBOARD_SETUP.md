# AITRAPP Dashboard Setup Guide

## 📁 Folder Structure

If you've created `aitrapp-dashboard` folder under AITRAPP, here's the recommended structure:

```
AITRAPP/
├── aitrapp-dashboard/          # New Gemini-powered dashboard
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Main dashboard
│   │   ├── api/
│   │   │   └── gemini/
│   │   │       └── route.ts    # Gemini API proxy
│   │   └── strategies/
│   │       └── [name]/
│   │           └── page.tsx   # Strategy detail
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── PortfolioCard.tsx
│   │   │   ├── StrategyGrid.tsx
│   │   │   ├── PositionsTable.tsx
│   │   │   └── OrdersTable.tsx
│   │   ├── ai/
│   │   │   ├── GeminiChat.tsx
│   │   │   ├── InsightPanel.tsx
│   │   │   └── RiskAnalysis.tsx
│   │   └── ui/                # shadcn/ui components
│   ├── hooks/
│   │   ├── usePortfolio.ts
│   │   ├── useStrategies.ts
│   │   ├── useGemini.ts
│   │   └── useWebSocket.ts
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── gemini.ts           # Gemini integration
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   ├── .env.local              # Environment variables
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
└── apps/
    └── ops-browser/            # Existing Next.js dashboard
```

## 🚀 Quick Start

### 1. Initialize Next.js Project (if not done)

```bash
cd /Users/mac/CRYPTO/AITRAPP/aitrapp-dashboard
npx create-next-app@latest . --typescript --tailwind --app --yes
```

### 2. Install Dependencies

```bash
npm install @google/generative-ai @tanstack/react-query zustand recharts
npm install -D @types/node
```

### 3. Set Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Copy from Existing Ops Browser (Optional)

If you want to reuse components from `apps/ops-browser`:

```bash
# Copy useful hooks
cp -r apps/ops-browser/hooks aitrapp-dashboard/

# Copy API client
cp apps/ops-browser/lib/api.ts aitrapp-dashboard/lib/

# Copy UI components
cp -r apps/ops-browser/components/ui aitrapp-dashboard/components/
```

## 🔌 API Integration

### Base API Client

Create `lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function fetchPortfolio() {
  const res = await fetch(`${API_BASE}/api/portfolio/snapshot`);
  if (!res.ok) throw new Error('Failed to fetch portfolio');
  return res.json();
}

export async function fetchStrategies() {
  const res = await fetch(`${API_BASE}/api/strategies/summary`);
  if (!res.ok) throw new Error('Failed to fetch strategies');
  return res.json();
}

export async function fetchIndices() {
  const res = await fetch(`${API_BASE}/api/market/indices`);
  if (!res.ok) throw new Error('Failed to fetch indices');
  return res.json();
}
```

## 🤖 Gemini 3 Pro Integration

### Create Gemini Client

Create `lib/gemini.ts`:

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(
  process.env.NEXT_PUBLIC_GEMINI_API_KEY!
);

export async function getGeminiInsight(
  prompt: string,
  context: any
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' });
  
  const fullPrompt = `
You are a trading operations analyst for AITRAPP (Autonomous Intelligent Trading Application).

Current Portfolio Context:
${JSON.stringify(context, null, 2)}

User Question: ${prompt}

Provide a concise, actionable analysis with specific recommendations.
  `;
  
  const result = await model.generateContent(fullPrompt);
  return result.response.text();
}
```

### Create API Route (Server-Side)

Create `app/api/gemini/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getGeminiInsight } from '@/lib/gemini';

export async function POST(request: NextRequest) {
  try {
    const { prompt, context } = await request.json();
    
    const insight = await getGeminiInsight(prompt, context);
    
    return NextResponse.json({ insight });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to generate insight' },
      { status: 500 }
    );
  }
}
```

## 📊 Main Dashboard Page

Create `app/page.tsx`:

```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio, fetchStrategies, fetchIndices } from '@/lib/api';
import { PortfolioCard } from '@/components/dashboard/PortfolioCard';
import { StrategyGrid } from '@/components/dashboard/StrategyGrid';
import { PositionsTable } from '@/components/dashboard/PositionsTable';

export default function Dashboard() {
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 5000, // 5 seconds
  });

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: fetchStrategies,
    refetchInterval: 10000, // 10 seconds
  });

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: fetchIndices,
    refetchInterval: 1000, // 1 second
  });

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <h1 className="text-3xl font-bold mb-6">AITRAPP Mission Control</h1>
      
      {/* Live Indices */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {indices && (
          <>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <div className="text-sm text-zinc-400">NIFTY 50</div>
              <div className="text-2xl font-bold">{indices['NIFTY 50']?.ltp}</div>
            </div>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <div className="text-sm text-zinc-400">BANKNIFTY</div>
              <div className="text-2xl font-bold">{indices.BANKNIFTY?.ltp}</div>
            </div>
          </>
        )}
      </div>

      {/* Portfolio Summary */}
      {portfolio && <PortfolioCard portfolio={portfolio} />}

      {/* Strategy Grid */}
      {strategies && <StrategyGrid strategies={strategies.strategies} />}

      {/* Positions Table */}
      {portfolio && <PositionsTable positions={portfolio.positions} />}
    </div>
  );
}
```

## 🎨 Design System

### Tailwind Config

Update `tailwind.config.ts`:

```typescript
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        zinc: {
          950: '#09090b',
          900: '#18181b',
          800: '#27272a',
        },
      },
    },
  },
  plugins: [],
};
```

## ✅ Next Steps

1. **Build Components**: Create the dashboard components (PortfolioCard, StrategyGrid, etc.)
2. **Add Gemini Chat**: Implement the AI chat interface
3. **Real-time Updates**: Set up WebSocket or polling for live data
4. **Error Handling**: Add error boundaries and loading states
5. **Testing**: Test with your running API at `http://localhost:8000`

## 🔗 Integration with Existing System

Your dashboard will connect to:
- **API**: `http://localhost:8000` (FastAPI backend)
- **Endpoints**: All endpoints from `GEMINI_STUDIO_PROMPT_CONCISE.md`
- **CORS**: Already configured in `apps/api/main.py`

## 📝 Notes

- The existing `apps/ops-browser` is a separate Next.js app
- This new `aitrapp-dashboard` can coexist or replace it
- Use the Gemini prompts from `GEMINI_STUDIO_PROMPT_CONCISE.md` for AI features
- Reference `web_dashboard.html` for design inspiration

## 🚨 Important

Make sure your FastAPI backend is running:
```bash
cd /Users/mac/CRYPTO/AITRAPP
./go_live.sh
```

Then start the dashboard:
```bash
cd aitrapp-dashboard
npm run dev
```

Access at: `http://localhost:3000`




## 📁 Folder Structure

If you've created `aitrapp-dashboard` folder under AITRAPP, here's the recommended structure:

```
AITRAPP/
├── aitrapp-dashboard/          # New Gemini-powered dashboard
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Main dashboard
│   │   ├── api/
│   │   │   └── gemini/
│   │   │       └── route.ts    # Gemini API proxy
│   │   └── strategies/
│   │       └── [name]/
│   │           └── page.tsx   # Strategy detail
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── PortfolioCard.tsx
│   │   │   ├── StrategyGrid.tsx
│   │   │   ├── PositionsTable.tsx
│   │   │   └── OrdersTable.tsx
│   │   ├── ai/
│   │   │   ├── GeminiChat.tsx
│   │   │   ├── InsightPanel.tsx
│   │   │   └── RiskAnalysis.tsx
│   │   └── ui/                # shadcn/ui components
│   ├── hooks/
│   │   ├── usePortfolio.ts
│   │   ├── useStrategies.ts
│   │   ├── useGemini.ts
│   │   └── useWebSocket.ts
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── gemini.ts           # Gemini integration
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   ├── .env.local              # Environment variables
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
└── apps/
    └── ops-browser/            # Existing Next.js dashboard
```

## 🚀 Quick Start

### 1. Initialize Next.js Project (if not done)

```bash
cd /Users/mac/CRYPTO/AITRAPP/aitrapp-dashboard
npx create-next-app@latest . --typescript --tailwind --app --yes
```

### 2. Install Dependencies

```bash
npm install @google/generative-ai @tanstack/react-query zustand recharts
npm install -D @types/node
```

### 3. Set Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Copy from Existing Ops Browser (Optional)

If you want to reuse components from `apps/ops-browser`:

```bash
# Copy useful hooks
cp -r apps/ops-browser/hooks aitrapp-dashboard/

# Copy API client
cp apps/ops-browser/lib/api.ts aitrapp-dashboard/lib/

# Copy UI components
cp -r apps/ops-browser/components/ui aitrapp-dashboard/components/
```

## 🔌 API Integration

### Base API Client

Create `lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function fetchPortfolio() {
  const res = await fetch(`${API_BASE}/api/portfolio/snapshot`);
  if (!res.ok) throw new Error('Failed to fetch portfolio');
  return res.json();
}

export async function fetchStrategies() {
  const res = await fetch(`${API_BASE}/api/strategies/summary`);
  if (!res.ok) throw new Error('Failed to fetch strategies');
  return res.json();
}

export async function fetchIndices() {
  const res = await fetch(`${API_BASE}/api/market/indices`);
  if (!res.ok) throw new Error('Failed to fetch indices');
  return res.json();
}
```

## 🤖 Gemini 3 Pro Integration

### Create Gemini Client

Create `lib/gemini.ts`:

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(
  process.env.NEXT_PUBLIC_GEMINI_API_KEY!
);

export async function getGeminiInsight(
  prompt: string,
  context: any
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' });
  
  const fullPrompt = `
You are a trading operations analyst for AITRAPP (Autonomous Intelligent Trading Application).

Current Portfolio Context:
${JSON.stringify(context, null, 2)}

User Question: ${prompt}

Provide a concise, actionable analysis with specific recommendations.
  `;
  
  const result = await model.generateContent(fullPrompt);
  return result.response.text();
}
```

### Create API Route (Server-Side)

Create `app/api/gemini/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getGeminiInsight } from '@/lib/gemini';

export async function POST(request: NextRequest) {
  try {
    const { prompt, context } = await request.json();
    
    const insight = await getGeminiInsight(prompt, context);
    
    return NextResponse.json({ insight });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to generate insight' },
      { status: 500 }
    );
  }
}
```

## 📊 Main Dashboard Page

Create `app/page.tsx`:

```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio, fetchStrategies, fetchIndices } from '@/lib/api';
import { PortfolioCard } from '@/components/dashboard/PortfolioCard';
import { StrategyGrid } from '@/components/dashboard/StrategyGrid';
import { PositionsTable } from '@/components/dashboard/PositionsTable';

export default function Dashboard() {
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 5000, // 5 seconds
  });

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: fetchStrategies,
    refetchInterval: 10000, // 10 seconds
  });

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: fetchIndices,
    refetchInterval: 1000, // 1 second
  });

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <h1 className="text-3xl font-bold mb-6">AITRAPP Mission Control</h1>
      
      {/* Live Indices */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {indices && (
          <>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <div className="text-sm text-zinc-400">NIFTY 50</div>
              <div className="text-2xl font-bold">{indices['NIFTY 50']?.ltp}</div>
            </div>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <div className="text-sm text-zinc-400">BANKNIFTY</div>
              <div className="text-2xl font-bold">{indices.BANKNIFTY?.ltp}</div>
            </div>
          </>
        )}
      </div>

      {/* Portfolio Summary */}
      {portfolio && <PortfolioCard portfolio={portfolio} />}

      {/* Strategy Grid */}
      {strategies && <StrategyGrid strategies={strategies.strategies} />}

      {/* Positions Table */}
      {portfolio && <PositionsTable positions={portfolio.positions} />}
    </div>
  );
}
```

## 🎨 Design System

### Tailwind Config

Update `tailwind.config.ts`:

```typescript
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        zinc: {
          950: '#09090b',
          900: '#18181b',
          800: '#27272a',
        },
      },
    },
  },
  plugins: [],
};
```

## ✅ Next Steps

1. **Build Components**: Create the dashboard components (PortfolioCard, StrategyGrid, etc.)
2. **Add Gemini Chat**: Implement the AI chat interface
3. **Real-time Updates**: Set up WebSocket or polling for live data
4. **Error Handling**: Add error boundaries and loading states
5. **Testing**: Test with your running API at `http://localhost:8000`

## 🔗 Integration with Existing System

Your dashboard will connect to:
- **API**: `http://localhost:8000` (FastAPI backend)
- **Endpoints**: All endpoints from `GEMINI_STUDIO_PROMPT_CONCISE.md`
- **CORS**: Already configured in `apps/api/main.py`

## 📝 Notes

- The existing `apps/ops-browser` is a separate Next.js app
- This new `aitrapp-dashboard` can coexist or replace it
- Use the Gemini prompts from `GEMINI_STUDIO_PROMPT_CONCISE.md` for AI features
- Reference `web_dashboard.html` for design inspiration

## 🚨 Important

Make sure your FastAPI backend is running:
```bash
cd /Users/mac/CRYPTO/AITRAPP
./go_live.sh
```

Then start the dashboard:
```bash
cd aitrapp-dashboard
npm run dev
```

Access at: `http://localhost:3000`





