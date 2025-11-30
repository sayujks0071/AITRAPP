# Express Server for KiteConnect Login and Trading

This Express.js server provides a simple interface for KiteConnect authentication and trading operations.

## Features

- ✅ KiteConnect OAuth login flow
- ✅ Automatic token management and .env file updates
- ✅ Trading endpoints to start/stop the Python trading backend
- ✅ Direct KiteConnect API access for positions, orders, and order placement
- ✅ Session management

## Setup

### 1. Install Dependencies

```bash
cd apps/express-server
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_REDIRECT_URL=http://localhost:3001/api/login/callback
```

**Important**: Make sure to register the redirect URL in your Kite Connect app settings:
1. Go to https://developers.kite.trade/apps/
2. Find your app
3. Add redirect URL: `http://localhost:3001/api/login/callback`
4. Save

### 3. Start Server

```bash
# Development mode (with auto-reload)
npm run dev

# Production mode
npm start
```

Server will start on `http://localhost:3001`

## API Endpoints

### Login Endpoints

#### `GET /api/login/initiate`
Get the login URL to redirect user to Kite login page.

**Response:**
```json
{
  "success": true,
  "loginUrl": "https://kite.trade/connect/login?...",
  "message": "Visit this URL to login to Kite",
  "redirectUrl": "http://localhost:3001/api/login/callback"
}
```

#### `GET /api/login/callback`
OAuth callback endpoint (called by Kite after login).

**Query Parameters:**
- `request_token`: Request token from Kite
- `status`: Login status (should be "success")

#### `POST /api/login/token`
Manually set access token (for non-OAuth flow).

**Body:**
```json
{
  "accessToken": "your_access_token",
  "userId": "your_user_id"
}
```

#### `GET /api/login/status`
Check current login status.

**Response:**
```json
{
  "authenticated": true,
  "user": {
    "userId": "AB1234",
    "userName": "John Doe",
    "email": "john@example.com"
  },
  "sessionActive": true
}
```

#### `POST /api/login/logout`
Logout and clear session.

### Trading Endpoints

#### `POST /api/trading/start`
Start trading by launching the Python FastAPI backend.

**Body (optional):**
```json
{
  "mode": "LIVE",
  "config": "configs/kite_day1_live.yaml"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Trading started successfully",
  "pid": 12345,
  "mode": "LIVE",
  "apiUrl": "http://localhost:8000"
}
```

#### `POST /api/trading/stop`
Stop trading by killing the Python process.

#### `GET /api/trading/status`
Get current trading status.

**Response:**
```json
{
  "trading": true,
  "processRunning": true,
  "pid": 12345,
  "authenticated": true,
  "apiStatus": {
    "mode": "LIVE",
    "is_paused": false,
    "positions_count": 2
  }
}
```

#### `GET /api/trading/positions`
Get current positions from KiteConnect.

#### `GET /api/trading/orders`
Get current orders from KiteConnect.

#### `POST /api/trading/place-order`
Place an order via KiteConnect.

**Body:**
```json
{
  "tradingsymbol": "NIFTY24NOVFUT",
  "exchange": "NFO",
  "transaction_type": "BUY",
  "quantity": 25,
  "order_type": "MARKET",
  "product": "MIS",
  "price": null,
  "validity": "DAY"
}
```

## Usage Flow

### 1. Login Flow

```bash
# Step 1: Get login URL
curl http://localhost:3001/api/login/initiate

# Step 2: Visit the loginUrl in browser and login
# Step 3: After login, Kite will redirect to callback URL
# Step 4: Check status
curl http://localhost:3001/api/login/status
```

### 2. Start Trading

```bash
# Start trading (requires authentication)
curl -X POST http://localhost:3001/api/trading/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "LIVE"}'

# Check trading status
curl http://localhost:3001/api/trading/status
```

### 3. Place Order Directly

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

## Integration with Python Backend

The Express server can start the Python FastAPI trading backend automatically. When you call `/api/trading/start`, it:

1. Verifies KiteConnect authentication
2. Launches the Python uvicorn server with the correct environment variables
3. Monitors the process and provides status updates

The Python backend will be available at `http://localhost:8000` with all its existing endpoints.

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing parameters)
- `401`: Unauthenticated
- `500`: Server error

Error responses include:
```json
{
  "error": "Error message",
  "message": "Detailed error description",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Security Notes

- Never commit `.env` file to version control
- Use strong `SESSION_SECRET` in production
- Enable HTTPS in production
- Set appropriate CORS origins
- Tokens expire daily - implement refresh logic

## Troubleshooting

### "KITE_API_KEY not set"
- Make sure `.env` file exists and contains `KITE_API_KEY` and `KITE_API_SECRET`

### "Login callback failed"
- Verify redirect URL is registered in Kite Connect app settings
- Check that `KITE_REDIRECT_URL` in `.env` matches the registered URL

### "Token expired"
- Tokens expire daily. Re-run login flow to get a new token.

### "Trading process failed to start"
- Make sure Python and uvicorn are installed
- Check that `apps/api/main.py` exists
- Verify all Python dependencies are installed

## Development

```bash
# Install dependencies
npm install

# Run with auto-reload
npm run dev

# Run tests (when implemented)
npm test
```

## License

ISC


