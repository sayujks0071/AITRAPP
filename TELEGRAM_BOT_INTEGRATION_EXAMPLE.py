"""
Example: Integrate Telegram Bot with Trading System

This shows how to connect the Telegram bot to your orchestrator
to send real-time notifications for trading events.

Add this code to apps/api/main.py or packages/core/orchestrator.py
"""

import os
from packages.integrations.telegram_bot import TradingTelegramBot

# ========================================
# Option 1: Add to FastAPI Startup
# ========================================

# In apps/api/main.py, add to @app.on_event("startup"):

async def startup_telegram_bot():
    """Initialize Telegram bot on API startup"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram bot not configured (missing token or chat_id)")
        return

    global telegram_bot
    telegram_bot = TradingTelegramBot(
        bot_token=bot_token,
        chat_id=chat_id,
        api_url="http://localhost:8000"
    )

    # Start bot in background
    await telegram_bot.start(use_redis=True, polling_enabled=True)

    logger.info("Telegram bot started successfully")


# ========================================
# Option 2: Add Hooks to Orchestrator
# ========================================

# In packages/core/orchestrator.py, add notification calls:

class TradingOrchestrator:
    def __init__(self, ..., telegram_bot: Optional[TradingTelegramBot] = None):
        # ... existing init code ...
        self.telegram_bot = telegram_bot

    async def _scan_cycle(self) -> None:
        """Execute one scan cycle: signals → rank → execute"""
        # ... existing code ...

        # When signal is generated (line ~731)
        for signal in all_signals:
            if self.telegram_bot:
                await self.telegram_bot.notify_signal_generated({
                    'strategy': signal.strategy_name,
                    'symbol': signal.instrument.symbol,
                    'side': signal.side.value,
                    'confidence': signal.confidence
                })

        # When order is placed (line ~850)
        if order_result.success:
            if self.telegram_bot:
                await self.telegram_bot.notify_order_placed({
                    'symbol': signal.instrument.tradingsymbol,
                    'side': signal.side.value,
                    'quantity': risk_check.position_size,
                    'price': signal.entry_price,
                    'order_id': order_result.order_id
                })

        # When order is filled (in execution callback)
        if order.status == "COMPLETE":
            if self.telegram_bot:
                await self.telegram_bot.notify_order_filled({
                    'symbol': order.tradingsymbol,
                    'side': order.transaction_type,
                    'quantity': order.quantity,
                    'fill_price': order.average_price
                })

        # When order is rejected
        if not order_result.success:
            if self.telegram_bot:
                await self.telegram_bot.notify_order_rejected({
                    'symbol': signal.instrument.tradingsymbol,
                    'reason': order_result.error_message
                })

    async def _close_position(self, position: Position, reason: ExitReason) -> None:
        """Close a position"""
        # ... existing code ...

        # After position is closed
        if self.telegram_bot:
            await self.telegram_bot.notify_position_closed({
                'symbol': position.instrument.tradingsymbol,
                'pnl': position.realized_pnl,
                'exit_reason': reason.value
            })

    async def _check_daily_loss_limit(self) -> None:
        """Check if daily loss limit approaching"""
        portfolio_risk = self._get_portfolio_risk()

        if portfolio_risk.daily_pnl < -self.risk_manager.daily_loss_limit * 0.8:
            if self.telegram_bot:
                await self.telegram_bot.notify_risk_alert(
                    alert_type="DAILY_LOSS_APPROACHING",
                    message=f"PnL: ₹{portfolio_risk.daily_pnl:,.2f} (80% of limit)"
                )

        # Send periodic PnL updates (every 1 hour)
        if self.telegram_bot and self._should_send_pnl_update():
            await self.telegram_bot.notify_daily_pnl_update(
                pnl=portfolio_risk.daily_pnl,
                limit=self.risk_manager.daily_loss_limit
            )


# ========================================
# Option 3: Redis Bus Integration
# ========================================

# If using Redis bus (packages/core/redis_bus.py):

class RedisBus:
    def __init__(self, ..., telegram_bot: Optional[TradingTelegramBot] = None):
        self.telegram_bot = telegram_bot

    async def publish_signal(self, signal_dict: Dict[str, Any]):
        """Publish signal to Redis and Telegram"""
        # ... existing Redis publish code ...

        # Also send to Telegram
        if self.telegram_bot:
            await self.telegram_bot.notify_signal_generated(signal_dict)

    async def publish_order(self, order_dict: Dict[str, Any]):
        """Publish order to Redis and Telegram"""
        # ... existing Redis publish code ...

        # Also send to Telegram
        if self.telegram_bot:
            status = order_dict.get('status')
            if status == 'PLACED':
                await self.telegram_bot.notify_order_placed(order_dict)
            elif status == 'COMPLETE':
                await self.telegram_bot.notify_order_filled(order_dict)
            elif status == 'REJECTED':
                await self.telegram_bot.notify_order_rejected(order_dict)


# ========================================
# Option 4: Market Data Monitor
# ========================================

# In packages/core/market_data.py, add connection monitoring:

class MarketDataStream:
    def __init__(self, ..., telegram_bot: Optional[TradingTelegramBot] = None):
        self.telegram_bot = telegram_bot
        self._was_connected = True

    def _on_disconnect(self):
        """Handle WebSocket disconnect"""
        # ... existing disconnect handling ...

        # Notify via Telegram
        if self.telegram_bot and self._was_connected:
            asyncio.create_task(
                self.telegram_bot.notify_marketdata_disconnected()
            )
            self._was_connected = False

    def _on_reconnect(self):
        """Handle WebSocket reconnect"""
        # ... existing reconnect handling ...

        self._was_connected = True


# ========================================
# Complete Integration Example
# ========================================

# In apps/api/main.py:

from fastapi import FastAPI
import os
from packages.integrations.telegram_bot import TradingTelegramBot

app = FastAPI()

# Global telegram bot instance
telegram_bot = None


@app.on_event("startup")
async def startup():
    """Initialize all services including Telegram bot"""
    global telegram_bot

    # Initialize Telegram bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if bot_token and chat_id:
        telegram_bot = TradingTelegramBot(
            bot_token=bot_token,
            chat_id=chat_id,
            api_url="http://localhost:8000"
        )
        await telegram_bot.start(use_redis=True, polling_enabled=True)
        logger.info("Telegram bot started")
    else:
        logger.warning("Telegram bot not configured")

    # Initialize other services (orchestrator, market data, etc.)
    # Pass telegram_bot to orchestrator
    orchestrator = TradingOrchestrator(
        # ... other params ...
        telegram_bot=telegram_bot  # ← Pass bot instance
    )

    # Store in app state
    app.state.orchestrator = orchestrator
    app.state.telegram_bot = telegram_bot


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    if telegram_bot:
        await telegram_bot.send_notification(
            "🔴 *Trading Bot Stopped*\n\n"
            "System is shutting down."
        )


# ========================================
# Usage Summary
# ========================================

"""
1. Set environment variables:
   export TELEGRAM_BOT_TOKEN="your_token"
   export TELEGRAM_CHAT_ID="your_chat_id"

2. Install dependencies:
   pip install python-telegram-bot aiohttp redis

3. Test bot:
   python scripts/test_telegram_bot.py

4. Integrate with orchestrator:
   - Option A: Standalone (run separately)
     python -m packages.integrations.telegram_bot

   - Option B: Integrated (within main app)
     Add to apps/api/main.py as shown above

5. Receive notifications:
   - Signal generated → 🎯 Telegram notification
   - Order placed → 📤 Telegram notification
   - Order filled → 🟢 Telegram notification
   - Position closed → 💰 Telegram notification
   - Risk alert → 🚨 Telegram notification

6. Query system via Telegram:
   /status → System status
   /pnl → Daily PnL
   /positions → Open positions
   /signals → OptionsRanker activity
   /risk → Risk metrics
   /metrics → Observability data
"""
