/**
 * KiteConnect Service
 * Handles all KiteConnect API interactions
 */

const KiteConnect = require('kiteconnect').KiteConnect;

class KiteService {
  constructor() {
    this.apiKey = process.env.KITE_API_KEY;
    this.apiSecret = process.env.KITE_API_SECRET;
    this.kite = null;
    this.accessToken = null;
  }

  /**
   * Initialize KiteConnect instance
   */
  initialize() {
    if (!this.apiKey) {
      throw new Error('KITE_API_KEY not set in environment');
    }

    this.kite = new KiteConnect({
      api_key: this.apiKey
    });

    // Try to load access token from environment
    if (process.env.KITE_ACCESS_TOKEN) {
      this.setAccessToken(process.env.KITE_ACCESS_TOKEN);
    }
  }

  /**
   * Generate access token from request token
   */
  async generateAccessToken(requestToken) {
    try {
      if (!this.apiSecret) {
        throw new Error('KITE_API_SECRET not set in environment');
      }

      if (!this.kite) {
        this.initialize();
      }

      const data = await this.kite.generateSession(requestToken, this.apiSecret);
      
      this.setAccessToken(data.access_token || data.accessToken);
      
      return {
        access_token: data.access_token || data.accessToken,
        user_id: data.user_id || data.userId,
        public_token: data.public_token || data.publicToken,
        login_time: data.login_time || data.loginTime
      };
    } catch (error) {
      console.error('Generate access token error:', error);
      throw error;
    }
  }

  /**
   * Set access token
   */
  setAccessToken(accessToken) {
    this.accessToken = accessToken;
    
    if (this.kite) {
      this.kite.setAccessToken(accessToken);
    } else {
      this.initialize();
      this.kite.setAccessToken(accessToken);
    }
  }

  /**
   * Get current access token
   */
  getAccessToken() {
    return this.accessToken;
  }

  /**
   * Check if authenticated
   */
  isAuthenticated() {
    return !!(this.kite && this.accessToken);
  }

  /**
   * Get user profile
   */
  async getProfile() {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      return await this.kite.getProfile();
    } catch (error) {
      console.error('Get profile error:', error);
      throw error;
    }
  }

  /**
   * Get positions
   */
  async getPositions() {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const positions = await this.kite.getPositions();
      return positions;
    } catch (error) {
      console.error('Get positions error:', error);
      throw error;
    }
  }

  /**
   * Get orders
   */
  async getOrders() {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const orders = await this.kite.getOrders();
      return orders;
    } catch (error) {
      console.error('Get orders error:', error);
      throw error;
    }
  }

  /**
   * Place an order
   */
  async placeOrder(orderParams) {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const orderId = await this.kite.placeOrder('regular', orderParams);
      return orderId;
    } catch (error) {
      console.error('Place order error:', error);
      throw error;
    }
  }

  /**
   * Cancel an order
   */
  async cancelOrder(orderId, variety = 'regular') {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const result = await this.kite.cancelOrder(variety, orderId);
      return result;
    } catch (error) {
      console.error('Cancel order error:', error);
      throw error;
    }
  }

  /**
   * Get margins
   */
  async getMargins() {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const margins = await this.kite.margins();
      return margins;
    } catch (error) {
      console.error('Get margins error:', error);
      throw error;
    }
  }

  /**
   * Get quote
   */
  async getQuote(instruments) {
    if (!this.isAuthenticated()) {
      throw new Error('Not authenticated');
    }

    try {
      const quote = await this.kite.quote(instruments);
      return quote;
    } catch (error) {
      console.error('Get quote error:', error);
      throw error;
    }
  }

  /**
   * Logout
   */
  logout() {
    this.kite = null;
    this.accessToken = null;
  }
}

// Export singleton instance
const kiteService = new KiteService();
kiteService.initialize();

module.exports = { kiteService };

