/**
 * Express Server for KiteConnect Login and Trading
 * ================================================
 * 
 * This server provides:
 * 1. KiteConnect OAuth login flow
 * 2. Trading endpoints to start/stop trading
 * 3. Integration with KiteConnect API
 */

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const session = require('express-session');
require('dotenv').config();

const { loginRoutes } = require('./routes/login');
const { tradingRoutes } = require('./routes/trading');
const { kiteService } = require('./services/kiteService');

const app = express();
const PORT = process.env.EXPRESS_PORT || 3001;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true
}));

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use(session({
  secret: process.env.SESSION_SECRET || 'aitrapp-express-secret-key-change-in-production',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    kiteConnected: kiteService.isAuthenticated()
  });
});

// Routes
app.use('/api/login', loginRoutes);
app.use('/api/trading', tradingRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'AITRAPP Express Server',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      login: '/api/login',
      trading: '/api/trading'
    }
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Express server running on http://localhost:${PORT}`);
  console.log(`📋 Health check: http://localhost:${PORT}/health`);
  console.log(`🔐 Login endpoint: http://localhost:${PORT}/api/login`);
  console.log(`📈 Trading endpoint: http://localhost:${PORT}/api/trading`);
});

module.exports = app;


