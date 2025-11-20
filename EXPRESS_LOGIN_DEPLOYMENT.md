# Express Login & Deployment Workflow

## Overview

Automated daily authentication and strategy rollout workflow for AITRAPP trading system.

## Files Created/Updated

### 1. `scripts/express_login.py`
- **Purpose**: Entry point for express login with `--redirect-url` support
- **Features**:
  - Wrapper around `kite_express_login.py`
  - Supports non-interactive mode via `--redirect-url` argument
  - Extracts `request_token` from full callback URL

### 2. `scripts/kite_express_login.py` (Updated)
- **Purpose**: Core authentication script
- **Key Updates**:
  - ✅ Uses `python-dotenv` to load credentials from `.env` file
  - ✅ Verifies session by fetching user profile after token generation
  - ✅ Safely updates `.env` file without deleting other variables
  - ✅ Opens browser automatically for login
  - ✅ Handles both interactive and non-interactive modes

### 3. `go_live.sh` (Updated)
- **Purpose**: Complete deployment workflow
- **Features**:
  - ✅ Runs express login first
  - ✅ Exits immediately if login fails (exit code != 0)
  - ✅ Loads `.env` file before running scripts
  - ✅ Sets production environment variables:
    - `APP_MODE=LIVE`
    - `APP_CONFIG=configs/kite_day1_live.yaml`
    - `MAX_TOKENS_PER_SCAN=80`
  - ✅ Launches uvicorn on `0.0.0.0:8000`
  - ✅ Colored output for better visibility
  - ✅ Proper error handling

## Usage

### Interactive Mode (Recommended)
```bash
./go_live.sh
```

This will:
1. Open browser for Kite login
2. Prompt you to paste the callback URL
3. Update `.env` with new token
4. Verify session
5. Launch trading engine

### Non-Interactive Mode
```bash
python3 scripts/express_login.py --redirect-url "http://localhost:8080/callback?request_token=XXXXX&action=login&status=success"
```

Then manually launch:
```bash
export APP_MODE=LIVE
export APP_CONFIG=configs/kite_day1_live.yaml
export MAX_TOKENS_PER_SCAN=80
python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Requirements

### Python Dependencies
```bash
pip install python-dotenv kiteconnect
```

### Environment Variables
The `.env` file must contain:
```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
```

## Workflow Steps

1. **Authentication** (`scripts/express_login.py`)
   - Loads credentials from `.env`
   - Opens Kite login URL in browser
   - Captures callback URL
   - Generates access token
   - Updates `.env` file safely
   - Verifies session by fetching profile

2. **Deployment** (`go_live.sh`)
   - Validates `.env` file exists
   - Runs express login
   - Sets production environment variables
   - Launches uvicorn server

## Error Handling

- ✅ Missing `.env` file → Clear error message
- ✅ Missing credentials → Clear error message
- ✅ Login failure → Script exits with code 1
- ✅ Token update failure → Warning but continues
- ✅ Session verification failure → Warning but continues

## Safety Features

- ✅ `.env` file updates preserve all existing variables
- ✅ Uses regex to find and replace specific lines only
- ✅ Preserves file structure and comments
- ✅ Validates token before saving
- ✅ Verifies session after token generation

## Testing

To test the workflow:

```bash
# Test credential loading
python3 -c "import sys; sys.path.insert(0, 'scripts'); from kite_express_login import get_credentials; print(get_credentials())"

# Test .env update (dry run)
# Create a test .env file and verify update function preserves other vars
```

## Troubleshooting

### Issue: "python-dotenv not installed"
**Solution**: `pip install python-dotenv`

### Issue: "kiteconnect not installed"
**Solution**: `pip install kiteconnect`

### Issue: "Browser doesn't open automatically"
**Solution**: Manually visit the URL printed in console

### Issue: "Token update fails"
**Solution**: Check `.env` file permissions (should be writable)

## Next Steps

- [ ] Add token expiry detection
- [ ] Add automatic token refresh before expiry
- [ ] Add health check after deployment
- [ ] Add logging to file
- [ ] Add email/telegram notifications on deployment

