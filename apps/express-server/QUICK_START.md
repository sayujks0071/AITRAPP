# Express Server Quick Start Guide

## Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
cd apps/express-server
npm install
```

### 2. Create .env File

Create a `.env` file in `apps/express-server/` with:

```env
# KiteConnect API Credentials
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here

# Redirect URL for OAuth callback
KITE_REDIRECT_URL=http://localhost:3001/api/login/callback

# Server Configuration
EXPRESS_PORT=3001
NODE_ENV=development
SESSION_SECRET=your-session-secret-key-change-in-production

# CORS Configuration
CORS_ORIGIN=http://localhost:3000
```

### 3. Register Redirect URL

**IMPORTANT**: Before starting, register the redirect URL in Kite Connect:

1. Go to https://developers.kite.trade/apps/
2. Find your app (or create one)
3. Add redirect URL: `http://localhost:3001/api/login/callback`
4. Save

### 4. Start Server

```bash
# Option 1: Use the startup script
./start.sh

# Option 2: Use npm
npm start

# Option 3: Development mode (auto-reload)
npm run dev
```

Server will start on `http://localhost:3001`

## Login Flow

### Step 1: Get Login URL

```bash
curl http://localhost:3001/api/login/initiate
```

Response:
```json
{
  "success": true,
  "loginUrl": "https://kite.trade/connect/login?api_key=...",
  "redirectUrl": "http://localhost:3001/api/login/callback"
}
```

### Step 2: Login

1. Open the `loginUrl` in your browser
2. Login with your Zerodha credentials
3. Complete 2FA if prompted
4. You'll be redirected to the callback URL automatically

### Step 3: Verify Login

```bash
curl http://localhost:3001/api/login/status
```

## Start Trading

Once logged in, start trading:

```bash
curl -X POST http://localhost:3001/api/trading/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "LIVE"}'
```

This will:
1. Verify your authentication
2. Launch the Python FastAPI trading backend
3. Start trading with your configured strategies

### Check Trading Status

```bash
curl http://localhost:3001/api/trading/status
```

### Stop Trading

```bash
curl -X POST http://localhost:3001/api/trading/stop
```

## Direct Trading (Without Python Backend)

You can also place orders directly via the Express server:

### Get Positions

```bash
curl http://localhost:3001/api/trading/positions
```

### Get Orders

```bash
curl http://localhost:3001/api/trading/orders
```

### Place Order

```bash
curl -X POST http://localhost:3001/api/trading/place-order \
  -H "Content-Type: application/json" \
  -d '{
    "tradingsymbol": "NIFTY24NOVFUT",
    "exchange": "NFO",
    "transaction_type": "BUY",
    "quantity": 25,
    "order_type": "MARKET",
    "product": "MIS"
  }'
```

## Complete Example

```bash
# 1. Start server
cd apps/express-server
npm start

# 2. In another terminal, get login URL
curl http://localhost:3001/api/login/initiate

# 3. Visit the loginUrl in browser and login

# 4. Check login status
curl http://localhost:3001/api/login/status

# 5. Start trading
curl -X POST http://localhost:3001/api/trading/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "LIVE"}'

# 6. Monitor trading
curl http://localhost:3001/api/trading/status
```

## Troubleshooting

### "KITE_API_KEY not set"
- Make sure `.env` file exists in `apps/express-server/`
- Check that `KITE_API_KEY` and `KITE_API_SECRET` are set

### "Login callback failed"
- Verify redirect URL is registered in Kite Connect app settings
- Check that `KITE_REDIRECT_URL` in `.env` matches the registered URL exactly

### "Token expired"
- Tokens expire daily. Re-run login flow to get a new token
- The server automatically updates `.env` with the new token

### "Trading process failed to start"
- Make sure Python 3 is installed: `python3 --version`
- Install Python dependencies: `pip install -r requirements.txt`
- Check that `apps/api/main.py` exists

## Next Steps

- Read the full [README.md](./README.md) for detailed API documentation
- Check the Python backend at `http://localhost:8000` when trading is active
- Monitor logs in the terminal for debugging


