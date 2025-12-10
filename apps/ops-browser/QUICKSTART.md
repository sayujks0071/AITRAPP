# Quick Start Guide

## Installation

```bash
cd apps/ops-browser
pnpm install
```

**Note:** If you don't have `pnpm`, install it first:
```bash
npm install -g pnpm
# or
brew install pnpm
```

## Development

### 1. Start the API (Terminal 1)

From project root:
```bash
make paper  # or make crypto-paper
```

### 2. Start the Dashboard (Terminal 2)

```bash
cd apps/ops-browser
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000)

## Smoke Tests

**From project root** (not from `apps/ops-browser`):

```bash
# API-only smoke test
make ops-smoke-no-ui

# Full smoke test (API + UI)
make ops-smoke
```

## Troubleshooting

### "Missing required metrics: trader_is_leader"

This means the API isn't running or the trader isn't started. Check:

```bash
# Is API running?
curl -fsS http://localhost:8000/health | jq

# Are metrics available?
curl -fsS http://localhost:8000/metrics | grep trader_is_leader
```

If not, start the API:
```bash
make paper  # or make crypto-paper
```

### "node_modules missing"

Install dependencies:
```bash
cd apps/ops-browser
pnpm install
```

### "make: No rule to make target 'ops-smoke'"

Run `make` commands from the **project root**, not from `apps/ops-browser`:

```bash
# ✅ Correct (from project root)
cd /Users/mac/CRYPTO/AITRAPP
make ops-smoke

# ❌ Wrong (from apps/ops-browser)
cd apps/ops-browser
make ops-smoke  # This won't work
```

### "next: command not found"

Install dependencies first:
```bash
cd apps/ops-browser
pnpm install
```

## Environment Setup

Create `.env.local` in `apps/ops-browser/`:

```bash
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > apps/ops-browser/.env.local
```
