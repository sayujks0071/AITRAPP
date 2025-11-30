/**
 * Login Routes for KiteConnect OAuth
 */

const express = require('express');
const router = express.Router();
const { kiteService } = require('../services/kiteService');
const fs = require('fs').promises;
const path = require('path');

/**
 * GET /api/login/initiate
 * Initiates KiteConnect login flow
 * Returns the login URL to redirect user
 */
router.get('/initiate', async (req, res) => {
  try {
    const apiKey = process.env.KITE_API_KEY;
    const apiSecret = process.env.KITE_API_SECRET;
    const redirectUrl = process.env.KITE_REDIRECT_URL || 'http://localhost:3001/api/login/callback';

    if (!apiKey || !apiSecret) {
      return res.status(400).json({
        error: 'KITE_API_KEY and KITE_API_SECRET must be set in .env file'
      });
    }

    // Generate login URL
    const loginUrl = `https://kite.trade/connect/login?api_key=${apiKey}&v=3&redirect_uri=${encodeURIComponent(redirectUrl)}`;

    res.json({
      success: true,
      loginUrl: loginUrl,
      message: 'Visit this URL to login to Kite',
      redirectUrl: redirectUrl
    });
  } catch (error) {
    console.error('Login initiation error:', error);
    res.status(500).json({
      error: 'Failed to initiate login',
      message: error.message
    });
  }
});

/**
 * GET /api/login/callback
 * Callback endpoint for KiteConnect OAuth redirect
 * Extracts request_token and generates access_token
 */
router.get('/callback', async (req, res) => {
  try {
    const requestToken = req.query.request_token;
    const status = req.query.status;

    if (!requestToken) {
      return res.status(400).json({
        error: 'Missing request_token in callback URL'
      });
    }

    if (status !== 'success') {
      return res.status(400).json({
        error: 'Login failed',
        status: status
      });
    }

    // Generate access token
    const authData = await kiteService.generateAccessToken(requestToken);

    if (!authData) {
      return res.status(500).json({
        error: 'Failed to generate access token'
      });
    }

    // Store in session
    req.session.kiteAccessToken = authData.access_token;
    req.session.kiteUserId = authData.user_id;

    // Update .env file
    await updateEnvFile(authData.access_token, authData.user_id);

    // Verify session by fetching profile
    const profile = await kiteService.getProfile();

    res.json({
      success: true,
      message: 'Login successful!',
      user: {
        userId: authData.user_id,
        userName: profile?.user_name || 'N/A',
        email: profile?.email || 'N/A'
      },
      tokenSaved: true
    });
  } catch (error) {
    console.error('Login callback error:', error);
    res.status(500).json({
      error: 'Login callback failed',
      message: error.message
    });
  }
});

/**
 * POST /api/login/token
 * Manually set access token (for non-OAuth flow)
 */
router.post('/token', async (req, res) => {
  try {
    const { accessToken, userId } = req.body;

    if (!accessToken) {
      return res.status(400).json({
        error: 'accessToken is required'
      });
    }

    // Set token in service
    kiteService.setAccessToken(accessToken);

    // Store in session
    req.session.kiteAccessToken = accessToken;
    if (userId) {
      req.session.kiteUserId = userId;
    }

    // Update .env file
    await updateEnvFile(accessToken, userId);

    // Verify session
    const profile = await kiteService.getProfile();

    res.json({
      success: true,
      message: 'Token set successfully',
      user: {
        userId: userId || profile?.user_id || 'N/A',
        userName: profile?.user_name || 'N/A'
      }
    });
  } catch (error) {
    console.error('Token setting error:', error);
    res.status(500).json({
      error: 'Failed to set token',
      message: error.message
    });
  }
});

/**
 * GET /api/login/status
 * Check current login status
 */
router.get('/status', async (req, res) => {
  try {
    const isAuthenticated = kiteService.isAuthenticated();
    let profile = null;

    if (isAuthenticated) {
      try {
        profile = await kiteService.getProfile();
      } catch (error) {
        // Token might be expired
        console.warn('Profile fetch failed, token may be expired:', error.message);
      }
    }

    res.json({
      authenticated: isAuthenticated,
      user: profile ? {
        userId: profile.user_id,
        userName: profile.user_name,
        email: profile.email
      } : null,
      sessionActive: !!req.session.kiteAccessToken
    });
  } catch (error) {
    console.error('Status check error:', error);
    res.status(500).json({
      error: 'Failed to check status',
      message: error.message
    });
  }
});

/**
 * GET /api/login/token
 * Get current access token (for debugging/updating .env)
 */
router.get('/token', (req, res) => {
  try {
    const token = kiteService.getAccessToken();
    if (token) {
      res.json({
        success: true,
        accessToken: token,
        authenticated: kiteService.isAuthenticated()
      });
    } else {
      res.status(404).json({
        error: 'No token available'
      });
    }
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get token',
      message: error.message
    });
  }
});

/**
 * POST /api/login/logout
 * Logout and clear session
 */
router.post('/logout', (req, res) => {
  try {
    kiteService.logout();
    req.session.destroy((err) => {
      if (err) {
        console.error('Session destroy error:', err);
      }
    });

    res.json({
      success: true,
      message: 'Logged out successfully'
    });
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({
      error: 'Failed to logout',
      message: error.message
    });
  }
});

/**
 * Helper function to update .env file
 */
async function updateEnvFile(accessToken, userId) {
  try {
    const envPath = path.join(__dirname, '../../.env');
    
    let envContent = '';
    try {
      envContent = await fs.readFile(envPath, 'utf8');
    } catch (error) {
      // .env file doesn't exist, create it
      envContent = '';
    }

    // Update or add KITE_ACCESS_TOKEN
    if (envContent.includes('KITE_ACCESS_TOKEN=')) {
      envContent = envContent.replace(
        /KITE_ACCESS_TOKEN=.*/,
        `KITE_ACCESS_TOKEN=${accessToken}`
      );
    } else {
      envContent += `\nKITE_ACCESS_TOKEN=${accessToken}\n`;
    }

    // Update or add KITE_USER_ID
    if (userId) {
      if (envContent.includes('KITE_USER_ID=')) {
        envContent = envContent.replace(
          /KITE_USER_ID=.*/,
          `KITE_USER_ID=${userId}`
        );
      } else {
        envContent += `KITE_USER_ID=${userId}\n`;
      }
    }

    // Add refresh timestamp
    const timestamp = new Date().toISOString();
    if (envContent.includes('KITE_TOKEN_REFRESHED_AT=')) {
      envContent = envContent.replace(
        /KITE_TOKEN_REFRESHED_AT=.*/,
        `KITE_TOKEN_REFRESHED_AT=${timestamp}`
      );
    } else {
      envContent += `KITE_TOKEN_REFRESHED_AT=${timestamp}\n`;
    }

    await fs.writeFile(envPath, envContent, 'utf8');
    console.log('✅ .env file updated with new token');
  } catch (error) {
    console.error('⚠️  Failed to update .env file:', error.message);
    // Don't throw - this is not critical
  }
}

module.exports = { loginRoutes: router };

