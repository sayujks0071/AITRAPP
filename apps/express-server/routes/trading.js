/**
 * Trading Routes for KiteConnect API
 */

const express = require('express');
const router = express.Router();
const { kiteService } = require('../services/kiteService');
const { spawn } = require('child_process');
const path = require('path');

// Store trading process
let tradingProcess = null;
let isTradingActive = false;

/**
 * POST /api/trading/start
 * Start trading by launching the Python FastAPI backend
 */
router.post('/start', async (req, res) => {
  try {
    // Check if already trading
    if (isTradingActive) {
      return res.status(400).json({
        error: 'Trading is already active',
        trading: true
      });
    }

    // Verify authentication
    if (!kiteService.isAuthenticated()) {
      return res.status(401).json({
        error: 'Not authenticated. Please login first.',
        authenticated: false
      });
    }

    // Verify session by fetching profile
    try {
      await kiteService.getProfile();
    } catch (error) {
      return res.status(401).json({
        error: 'Token expired or invalid. Please login again.',
        authenticated: false
      });
    }

    // Start Python trading backend
    const repoRoot = path.join(__dirname, '../..');
    const pythonScript = path.join(repoRoot, 'apps/api/main.py');

    // Set environment variables
    const env = {
      ...process.env,
      APP_MODE: req.body.mode || 'LIVE',
      APP_CONFIG: req.body.config || 'configs/kite_day1_live.yaml',
      KITE_ACCESS_TOKEN: kiteService.getAccessToken()
    };

    // Launch uvicorn server
    tradingProcess = spawn('python3', [
      '-m', 'uvicorn',
      'apps.api.main:app',
      '--host', '0.0.0.0',
      '--port', '8000'
    ], {
      cwd: repoRoot,
      env: env,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // Handle process output
    tradingProcess.stdout.on('data', (data) => {
      console.log(`[Trading] ${data.toString()}`);
    });

    tradingProcess.stderr.on('data', (data) => {
      console.error(`[Trading Error] ${data.toString()}`);
    });

    tradingProcess.on('exit', (code) => {
      console.log(`[Trading] Process exited with code ${code}`);
      tradingProcess = null;
      isTradingActive = false;
    });

    tradingProcess.on('error', (error) => {
      console.error('[Trading] Process error:', error);
      tradingProcess = null;
      isTradingActive = false;
    });

    isTradingActive = true;

    // Wait a bit to check if process started successfully
    setTimeout(() => {
      if (tradingProcess && !tradingProcess.killed) {
        return res.json({
          success: true,
          message: 'Trading started successfully',
          pid: tradingProcess.pid,
          mode: env.APP_MODE,
          apiUrl: 'http://localhost:8000'
        });
      } else {
        isTradingActive = false;
        return res.status(500).json({
          error: 'Failed to start trading process'
        });
      }
    }, 2000);

  } catch (error) {
    console.error('Start trading error:', error);
    isTradingActive = false;
    res.status(500).json({
      error: 'Failed to start trading',
      message: error.message
    });
  }
});

/**
 * POST /api/trading/stop
 * Stop trading by killing the Python process
 */
router.post('/stop', async (req, res) => {
  try {
    if (!isTradingActive || !tradingProcess) {
      return res.json({
        success: true,
        message: 'Trading is not active',
        trading: false
      });
    }

    // Kill the process
    tradingProcess.kill('SIGTERM');

    // Wait for graceful shutdown
    setTimeout(() => {
      if (tradingProcess && !tradingProcess.killed) {
        tradingProcess.kill('SIGKILL');
      }
    }, 5000);

    tradingProcess = null;
    isTradingActive = false;

    res.json({
      success: true,
      message: 'Trading stopped successfully',
      trading: false
    });
  } catch (error) {
    console.error('Stop trading error:', error);
    res.status(500).json({
      error: 'Failed to stop trading',
      message: error.message
    });
  }
});

/**
 * GET /api/trading/status
 * Get current trading status
 */
router.get('/status', async (req, res) => {
  try {
    const status = {
      trading: isTradingActive,
      processRunning: tradingProcess && !tradingProcess.killed,
      pid: tradingProcess ? tradingProcess.pid : null,
      authenticated: kiteService.isAuthenticated()
    };

    // If trading is active, try to get status from Python API
    if (isTradingActive) {
      try {
        const axios = require('axios');
        const apiResponse = await axios.get('http://localhost:8000/state', {
          timeout: 2000
        });
        status.apiStatus = apiResponse.data;
      } catch (error) {
        status.apiError = 'Python API not responding';
      }
    }

    res.json(status);
  } catch (error) {
    console.error('Trading status error:', error);
    res.status(500).json({
      error: 'Failed to get trading status',
      message: error.message
    });
  }
});

/**
 * GET /api/trading/positions
 * Get current positions from KiteConnect
 */
router.get('/positions', async (req, res) => {
  try {
    if (!kiteService.isAuthenticated()) {
      return res.status(401).json({
        error: 'Not authenticated'
      });
    }

    const positions = await kiteService.getPositions();
    res.json({
      success: true,
      positions: positions
    });
  } catch (error) {
    console.error('Get positions error:', error);
    res.status(500).json({
      error: 'Failed to get positions',
      message: error.message
    });
  }
});

/**
 * GET /api/trading/orders
 * Get current orders from KiteConnect
 */
router.get('/orders', async (req, res) => {
  try {
    if (!kiteService.isAuthenticated()) {
      return res.status(401).json({
        error: 'Not authenticated'
      });
    }

    const orders = await kiteService.getOrders();
    res.json({
      success: true,
      orders: orders
    });
  } catch (error) {
    console.error('Get orders error:', error);
    res.status(500).json({
      error: 'Failed to get orders',
      message: error.message
    });
  }
});

/**
 * POST /api/trading/place-order
 * Place an order via KiteConnect
 */
router.post('/place-order', async (req, res) => {
  try {
    if (!kiteService.isAuthenticated()) {
      return res.status(401).json({
        error: 'Not authenticated'
      });
    }

    const {
      tradingsymbol,
      exchange,
      transaction_type,
      quantity,
      order_type,
      product,
      price,
      validity
    } = req.body;

    if (!tradingsymbol || !exchange || !transaction_type || !quantity || !order_type || !product) {
      return res.status(400).json({
        error: 'Missing required fields: tradingsymbol, exchange, transaction_type, quantity, order_type, product'
      });
    }

    const orderParams = {
      tradingsymbol,
      exchange,
      transaction_type,
      quantity: parseInt(quantity),
      order_type,
      product,
      price: price ? parseFloat(price) : undefined,
      validity: validity || 'DAY'
    };

    const orderId = await kiteService.placeOrder(orderParams);

    res.json({
      success: true,
      orderId: orderId,
      message: 'Order placed successfully'
    });
  } catch (error) {
    console.error('Place order error:', error);
    res.status(500).json({
      error: 'Failed to place order',
      message: error.message
    });
  }
});

module.exports = { tradingRoutes: router };

