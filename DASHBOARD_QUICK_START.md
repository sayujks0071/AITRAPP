# AITRAPP Dashboard - Quick Start

## 📁 Folder Location

If you've saved the dashboard as `aitrapp-dashboard` under AITRAPP:

```
/Users/mac/CRYPTO/AITRAPP/aitrapp-dashboard/
```

## 🚀 Setup Options

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/mac/CRYPTO/AITRAPP
./scripts/setup_dashboard.sh
```

### Option 2: Manual Setup

```bash
cd /Users/mac/CRYPTO/AITRAPP
mkdir -p aitrapp-dashboard
cd aitrapp-dashboard
npx create-next-app@latest . --typescript --tailwind --app --yes
```

## 📋 Essential Files Created

I've created these helper files for you:

1. **`AITRAPP_DASHBOARD_SETUP.md`** - Complete setup guide with code examples
2. **`GEMINI_STUDIO_PROMPT_CONCISE.md`** - Ready-to-use prompt for Gemini Studio
3. **`GEMINI_STUDIO_FRONTEND_PROMPT.md`** - Detailed prompt with full specifications
4. **`scripts/setup_dashboard.sh`** - Automated setup script

## 🔑 Environment Variables

Create `.env.local` in `aitrapp-dashboard/`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key_here
```

## 📦 Required Dependencies

```bash
cd aitrapp-dashboard
npm install @google/generative-ai @tanstack/react-query zustand recharts
```

## 🎯 Key Features to Implement

1. **Real-time Dashboard** - Live portfolio, positions, orders
2. **Strategy Status** - SCANNING vs DEPLOYED indicators
3. **Gemini AI Chat** - Natural language trading insights
4. **Live Indices** - NIFTY 50 & BANKNIFTY prices
5. **Portfolio Reconciliation** - ALGO vs MANUAL tags

## 🔗 API Endpoints

Your dashboard connects to:
- Base URL: `http://localhost:8000`
- Portfolio: `/api/portfolio/snapshot`
- Strategies: `/api/strategies/summary`
- Indices: `/api/market/indices`
- Positions: `/api/positions`
- Orders: `/api/orders`

## 🚀 Start Development

1. **Start Backend** (if not running):
   ```bash
   cd /Users/mac/CRYPTO/AITRAPP
   ./go_live.sh
   ```

2. **Start Dashboard**:
   ```bash
   cd aitrapp-dashboard
   npm run dev
   ```

3. **Open Browser**:
   ```
   http://localhost:3000
   ```

## 📚 Reference Documents

- **Setup Guide**: `AITRAPP_DASHBOARD_SETUP.md`
- **Gemini Prompt**: `GEMINI_STUDIO_PROMPT_CONCISE.md`
- **Existing Dashboard**: `web_dashboard.html` (for design reference)
- **Existing Next.js App**: `apps/ops-browser/` (for component patterns)

## ✅ Verification Checklist

- [ ] Dashboard folder created
- [ ] Next.js initialized
- [ ] Dependencies installed
- [ ] `.env.local` configured
- [ ] Backend API running on port 8000
- [ ] Dashboard accessible at `http://localhost:3000`

---

**Ready to build!** Use the Gemini Studio prompts to generate the frontend code, or follow the setup guide to build it manually.




## 📁 Folder Location

If you've saved the dashboard as `aitrapp-dashboard` under AITRAPP:

```
/Users/mac/CRYPTO/AITRAPP/aitrapp-dashboard/
```

## 🚀 Setup Options

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/mac/CRYPTO/AITRAPP
./scripts/setup_dashboard.sh
```

### Option 2: Manual Setup

```bash
cd /Users/mac/CRYPTO/AITRAPP
mkdir -p aitrapp-dashboard
cd aitrapp-dashboard
npx create-next-app@latest . --typescript --tailwind --app --yes
```

## 📋 Essential Files Created

I've created these helper files for you:

1. **`AITRAPP_DASHBOARD_SETUP.md`** - Complete setup guide with code examples
2. **`GEMINI_STUDIO_PROMPT_CONCISE.md`** - Ready-to-use prompt for Gemini Studio
3. **`GEMINI_STUDIO_FRONTEND_PROMPT.md`** - Detailed prompt with full specifications
4. **`scripts/setup_dashboard.sh`** - Automated setup script

## 🔑 Environment Variables

Create `.env.local` in `aitrapp-dashboard/`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key_here
```

## 📦 Required Dependencies

```bash
cd aitrapp-dashboard
npm install @google/generative-ai @tanstack/react-query zustand recharts
```

## 🎯 Key Features to Implement

1. **Real-time Dashboard** - Live portfolio, positions, orders
2. **Strategy Status** - SCANNING vs DEPLOYED indicators
3. **Gemini AI Chat** - Natural language trading insights
4. **Live Indices** - NIFTY 50 & BANKNIFTY prices
5. **Portfolio Reconciliation** - ALGO vs MANUAL tags

## 🔗 API Endpoints

Your dashboard connects to:
- Base URL: `http://localhost:8000`
- Portfolio: `/api/portfolio/snapshot`
- Strategies: `/api/strategies/summary`
- Indices: `/api/market/indices`
- Positions: `/api/positions`
- Orders: `/api/orders`

## 🚀 Start Development

1. **Start Backend** (if not running):
   ```bash
   cd /Users/mac/CRYPTO/AITRAPP
   ./go_live.sh
   ```

2. **Start Dashboard**:
   ```bash
   cd aitrapp-dashboard
   npm run dev
   ```

3. **Open Browser**:
   ```
   http://localhost:3000
   ```

## 📚 Reference Documents

- **Setup Guide**: `AITRAPP_DASHBOARD_SETUP.md`
- **Gemini Prompt**: `GEMINI_STUDIO_PROMPT_CONCISE.md`
- **Existing Dashboard**: `web_dashboard.html` (for design reference)
- **Existing Next.js App**: `apps/ops-browser/` (for component patterns)

## ✅ Verification Checklist

- [ ] Dashboard folder created
- [ ] Next.js initialized
- [ ] Dependencies installed
- [ ] `.env.local` configured
- [ ] Backend API running on port 8000
- [ ] Dashboard accessible at `http://localhost:3000`

---

**Ready to build!** Use the Gemini Studio prompts to generate the frontend code, or follow the setup guide to build it manually.





