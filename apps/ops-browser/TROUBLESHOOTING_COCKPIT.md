# Broker Cockpit Troubleshooting

## Component Location
- **Component**: `apps/ops-browser/components/portfolio/PortfolioPanel.tsx`
- **Hook**: `apps/ops-browser/hooks/usePortfolio.ts`
- **API Endpoint**: `GET /api/portfolio/snapshot`
- **Dashboard Integration**: `apps/ops-browser/app/page.tsx` (after P&L Row section)

## Quick Check

1. **Is the component visible?**
   - Look for a card titled "Broker Portfolio Cockpit" after the "P&L Row" section
   - It should appear between the P&L metrics and the Exchange Panel

2. **Is the API server running?**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy",...}`

3. **Is the API endpoint accessible?**
   ```bash
   curl http://localhost:8000/api/portfolio/snapshot
   ```
   Should return portfolio JSON or an error message

4. **Is Next.js dev server running?**
   ```bash
   cd apps/ops-browser
   npm run dev
   ```
   Should be running on http://localhost:3000

## Common Issues

### Component Not Visible

**Check browser console:**
- Open DevTools (F12)
- Look for errors in Console tab
- Check Network tab for failed requests to `/api/portfolio/snapshot`

**Check if component is rendering:**
- The component should show at least "Loading broker state..." or an error message
- If you see nothing, there might be a build error

**Restart Next.js dev server:**
```bash
cd apps/ops-browser
# Stop the server (Ctrl+C)
npm run dev
```

### API Connection Error

**Check CORS:**
- The API should allow requests from `http://localhost:3000`
- Check `apps/api/main.py` for CORS middleware configuration

**Check API server:**
```bash
# Make sure API is running
./go_live.sh

# Or check if it's already running
curl http://localhost:8000/health
```

### Component Shows Error

**If you see "Error: HTTP 503":**
- Kite client not initialized
- Position store not initialized
- API server needs to be restarted

**If you see "Error: Failed to fetch":**
- API server is not running
- CORS issue
- Network connectivity problem

## Manual Test

Add this temporary test component to verify rendering:

```tsx
// In app/page.tsx, add before PortfolioPanel:
<div className="p-4 bg-yellow-200 border-2 border-yellow-500">
  <strong>TEST: PortfolioPanel should appear below this</strong>
</div>
```

If you see the yellow box but not the PortfolioPanel, there's a component error.

## Expected Behavior

1. **On Load**: Shows "⏳ Loading broker state from Kite API..."
2. **On Success**: Shows Capital & Margin, Broker vs Algo, Positions
3. **On Error**: Shows error message with details
4. **Auto-refresh**: Updates every 10 seconds

## Debug Steps

1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for:
   - Component render errors
   - API fetch errors
   - Network request failures
4. Go to Network tab
5. Filter by "portfolio"
6. Check if `/api/portfolio/snapshot` request is being made
7. Check response status and body

## Force Refresh

If component is cached:
1. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. Clear browser cache
3. Restart Next.js dev server




