"""
Telegram Bot Integration for Real-Time Trading Updates

Connects to Redis bus and sends notifications for:
- Signal generation (OptionsRanker, G1, T1, D1)
- Order execution (placed, filled, rejected)
- Position updates (opened, closed, PnL)
- Risk alerts (daily loss approaching limit)
- System status (marketdata, leader lock, errors)
- Observability metrics (setups evaluated, filter rejections)

Setup:
1. Create bot via @BotFather on Telegram
2. Get bot token and your chat ID
3. Set environment variables:
   - TELEGRAM_BOT_TOKEN="your_bot_token"
   - TELEGRAM_CHAT_ID="your_chat_id"
4. Start bot: python -m packages.integrations.telegram_bot
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp

logger = structlog.get_logger(__name__)


class TradingTelegramBot:
    """Telegram bot for real-time trading notifications"""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        api_url: str = "http://localhost:8000",
        redis_url: str = "redis://localhost:6379/0"
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = api_url
        self.redis_url = redis_url

        # Telegram bot
        self.application = Application.builder().token(bot_token).build()
        self.bot = Bot(token=bot_token)

        # Redis subscriber (optional, for real-time events)
        self.redis_client = None

        # Register command handlers
        self._register_commands()

        # Message formatting
        self.max_message_length = 4096  # Telegram limit

    def _register_commands(self):
        """Register Telegram bot commands"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("pnl", self.cmd_pnl))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("signals", self.cmd_signals))
        self.application.add_handler(CommandHandler("risk", self.cmd_risk))
        self.application.add_handler(CommandHandler("metrics", self.cmd_metrics))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """
🤖 *Trading Bot Active*

I'll send you real-time updates for:
• Signal generation (OptionsRanker, G1, T1, D1)
• Order execution (placed, filled, rejected)
• Position updates (opened, closed, PnL)
• Risk alerts (approaching daily loss limit)
• System status (marketdata, errors)

*Commands:*
/status - System status
/pnl - Daily PnL
/positions - Open positions
/signals - Today's signals
/risk - Risk metrics
/metrics - Observability metrics
/help - Show all commands

Let's make some money! 💰
"""
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/state") as resp:
                    state = await resp.json()

                async with session.get(f"{self.api_url}/health") as resp:
                    health = await resp.json()

            msg = f"""
📊 *System Status*

Mode: `{state.get('mode', 'UNKNOWN')}`
Paused: `{state.get('is_paused', False)}`
Market Data: `{'✅ Connected' if state.get('marketdata_connected') else '❌ Disconnected'}`
WebSocket: `{'✅ Connected' if state.get('websocket_connected') else '❌ Disconnected'}`
Subscriptions: `{state.get('subscription_count', 0)}`

Positions: `{state.get('positions_count', 0)}`
Daily PnL: `₹{state.get('daily_pnl', 0):,.2f}`

Health: `{health.get('status', 'unknown')}`
Timestamp: `{datetime.now().strftime('%H:%M:%S IST')}`
"""
            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch status", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/risk") as resp:
                    risk = await resp.json()

            daily_pnl = risk.get('daily_pnl', 0)
            daily_loss_limit = risk.get('daily_loss_limit', 25000)

            # Determine emoji based on PnL
            if daily_pnl > 0:
                emoji = "🟢"
            elif daily_pnl < -daily_loss_limit * 0.5:
                emoji = "🔴"
            else:
                emoji = "🟡"

            msg = f"""
{emoji} *Daily PnL Report*

PnL: `₹{daily_pnl:,.2f}`
Loss Limit: `₹{daily_loss_limit:,.2f}`
Remaining: `₹{daily_loss_limit + daily_pnl:,.2f}`

Utilization: `{abs(daily_pnl / daily_loss_limit * 100):.1f}%`
"""
            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch PnL", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/positions") as resp:
                    data = await resp.json()

            positions = data.get('positions', [])

            if not positions:
                await update.message.reply_text("No open positions")
                return

            msg = "📈 *Open Positions*\n\n"
            for pos in positions:
                symbol = pos.get('tradingsymbol', 'UNKNOWN')
                qty = pos.get('quantity', 0)
                avg_price = pos.get('average_price', 0)
                ltp = pos.get('last_price', 0)
                pnl = pos.get('pnl', 0)

                side = "🟢 LONG" if qty > 0 else "🔴 SHORT"

                msg += f"""
{side} `{symbol}`
Qty: `{abs(qty)}` | Avg: `₹{avg_price:.2f}`
LTP: `₹{ltp:.2f}` | PnL: `₹{pnl:,.2f}`
───────────────────
"""

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch positions", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command - show OptionsRanker observability"""
        try:
            # Query observability metrics from Prometheus endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/metrics") as resp:
                    metrics_text = await resp.text()

            # Parse metrics
            setups_evaluated = 0
            rejections = {}
            signals_approved = 0

            for line in metrics_text.split('\n'):
                if line.startswith('options_ranker_setups_evaluated_total'):
                    setups_evaluated = int(float(line.split()[-1]))
                elif line.startswith('options_ranker_filter_rejections_total'):
                    # Extract filter name
                    if 'filter_name="' in line:
                        filter_name = line.split('filter_name="')[1].split('"')[0]
                        count = int(float(line.split()[-1]))
                        rejections[filter_name] = count
                elif line.startswith('options_ranker_signals_approved_total'):
                    signals_approved = int(float(line.split()[-1]))

            msg = f"""
🎯 *OptionsRanker Today*

Setups Evaluated: `{setups_evaluated}`
Signals Approved: `{signals_approved}`

"""

            if rejections:
                msg += "*Filter Rejections:*\n"
                for filter_name, count in rejections.items():
                    filter_display = filter_name.replace('_', ' ').title()
                    msg += f"• {filter_display}: `{count}`\n"
            else:
                msg += "*No rejections yet*\n"

            if setups_evaluated > 0:
                approval_rate = signals_approved / setups_evaluated * 100
                msg += f"\nApproval Rate: `{approval_rate:.1f}%`"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch signals", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/risk") as resp:
                    risk = await resp.json()

            msg = f"""
⚠️ *Risk Metrics*

Daily PnL: `₹{risk.get('daily_pnl', 0):,.2f}`
Daily Loss Limit: `₹{risk.get('daily_loss_limit', 25000):,.2f}`

Margin Used: `{risk.get('margin_used_pct', 0):.1f}%`
Portfolio Heat: `{risk.get('portfolio_heat_pct', 0):.2f}%`

Max Positions: `{risk.get('max_positions', 4)}`
Open Positions: `{risk.get('open_positions', 0)}`
"""
            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch risk", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /metrics command - full observability summary"""
        try:
            # Run the observability script
            import subprocess
            result = subprocess.run(
                ["bash", "/Users/mac/CRYPTO/AITRAPP/scripts/query_signal_metrics.sh"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse output and format for Telegram
            output = result.stdout

            # Extract key sections
            lines = output.split('\n')
            setups_line = next((l for l in lines if "Total Setups Evaluated:" in l), None)
            approved_line = next((l for l in lines if "Total Approved:" in l), None)
            top_blocker_line = next((l for l in lines if "Top blocker:" in l), None)

            msg = "📊 *Signal Observability*\n\n"
            if setups_line:
                msg += setups_line.strip() + "\n"
            if approved_line:
                msg += approved_line.strip() + "\n"
            if top_blocker_line:
                msg += "\n" + top_blocker_line.strip() + "\n"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error("Failed to fetch metrics", error=str(e))
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
🤖 *Available Commands*

/status - System status (mode, marketdata, positions)
/pnl - Daily PnL and loss limit utilization
/positions - Open positions with PnL
/signals - OptionsRanker signal generation today
/risk - Risk metrics (margin, heat, limits)
/metrics - Full observability summary
/help - Show this message

*Automatic Notifications:*
• Signal generated (OptionsRanker, G1, T1, D1)
• Order placed/filled/rejected
• Position opened/closed
• Risk alert (approaching daily loss limit)
• System error/warning
"""
        await update.message.reply_text(help_msg, parse_mode='Markdown')

    # ========================================
    # Real-Time Notifications (Push)
    # ========================================

    async def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """Send notification to user"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("Telegram notification sent", message_preview=message[:50])
        except Exception as e:
            logger.error("Failed to send Telegram notification", error=str(e))

    async def notify_signal_generated(self, signal: Dict[str, Any]):
        """Notify when a signal is generated"""
        strategy = signal.get('strategy', 'UNKNOWN')
        symbol = signal.get('symbol', 'UNKNOWN')
        side = signal.get('side', 'UNKNOWN')
        confidence = signal.get('confidence', 0)

        msg = f"""
🎯 *Signal Generated*

Strategy: `{strategy}`
Symbol: `{symbol}`
Side: `{side}`
Confidence: `{confidence:.2%}`

Waiting for risk approval...
"""
        await self.send_notification(msg)

    async def notify_order_placed(self, order: Dict[str, Any]):
        """Notify when an order is placed"""
        symbol = order.get('symbol', 'UNKNOWN')
        side = order.get('side', 'UNKNOWN')
        quantity = order.get('quantity', 0)
        price = order.get('price', 0)
        order_id = order.get('order_id', 'UNKNOWN')

        msg = f"""
📤 *Order Placed*

Symbol: `{symbol}`
Side: `{side}`
Qty: `{quantity}`
Price: `₹{price:.2f}`
Order ID: `{order_id}`

Status: Pending...
"""
        await self.send_notification(msg)

    async def notify_order_filled(self, order: Dict[str, Any]):
        """Notify when an order is filled"""
        symbol = order.get('symbol', 'UNKNOWN')
        side = order.get('side', 'UNKNOWN')
        quantity = order.get('quantity', 0)
        fill_price = order.get('fill_price', 0)

        emoji = "🟢" if side == "BUY" else "🔴"

        msg = f"""
{emoji} *Order Filled*

Symbol: `{symbol}`
Side: `{side}`
Qty: `{quantity}`
Fill Price: `₹{fill_price:.2f}`

Position opened ✅
"""
        await self.send_notification(msg)

    async def notify_order_rejected(self, order: Dict[str, Any]):
        """Notify when an order is rejected"""
        symbol = order.get('symbol', 'UNKNOWN')
        reason = order.get('reason', 'Unknown')

        msg = f"""
❌ *Order Rejected*

Symbol: `{symbol}`
Reason: `{reason}`

Position NOT opened
"""
        await self.send_notification(msg)

    async def notify_position_closed(self, position: Dict[str, Any]):
        """Notify when a position is closed"""
        symbol = position.get('symbol', 'UNKNOWN')
        pnl = position.get('pnl', 0)
        exit_reason = position.get('exit_reason', 'UNKNOWN')

        emoji = "🟢" if pnl > 0 else "🔴"

        msg = f"""
{emoji} *Position Closed*

Symbol: `{symbol}`
Exit Reason: `{exit_reason}`
PnL: `₹{pnl:,.2f}`

Position flattened ✅
"""
        await self.send_notification(msg)

    async def notify_daily_pnl_update(self, pnl: float, limit: float):
        """Notify daily PnL update"""
        utilization = abs(pnl / limit * 100) if limit > 0 else 0

        if pnl > 0:
            emoji = "🟢"
            status = "Profit"
        elif utilization > 80:
            emoji = "🔴"
            status = "⚠️ Near Limit"
        elif utilization > 50:
            emoji = "🟡"
            status = "Moderate Loss"
        else:
            emoji = "🟢"
            status = "Normal"

        msg = f"""
{emoji} *Daily PnL Update*

PnL: `₹{pnl:,.2f}`
Status: {status}
Utilization: `{utilization:.1f}%` of limit

Loss Limit: `₹{limit:,.2f}`
Remaining: `₹{limit + pnl:,.2f}`
"""
        await self.send_notification(msg)

    async def notify_risk_alert(self, alert_type: str, message: str):
        """Notify risk alert"""
        msg = f"""
🚨 *RISK ALERT*

Type: `{alert_type}`
Message: `{message}`

Check system immediately!
"""
        await self.send_notification(msg)

    async def notify_system_error(self, error_type: str, error_message: str):
        """Notify system error"""
        msg = f"""
❌ *System Error*

Type: `{error_type}`
Error: `{error_message}`

Check logs for details
"""
        await self.send_notification(msg)

    async def notify_marketdata_disconnected(self):
        """Notify when market data disconnects"""
        msg = """
⚠️ *Market Data Disconnected*

WebSocket connection lost
Strategies will not execute

Check connection immediately!
"""
        await self.send_notification(msg)

    # ========================================
    # Redis Bus Subscriber (Optional)
    # ========================================

    async def subscribe_to_events(self):
        """Subscribe to Redis bus events for real-time notifications"""
        try:
            import redis.asyncio as redis

            self.redis_client = redis.from_url(self.redis_url)
            pubsub = self.redis_client.pubsub()

            # Subscribe to channels
            await pubsub.subscribe(
                'signals',
                'decisions',
                'orders',
                'positions',
                'risk_alerts',
                'system_errors'
            )

            logger.info("Subscribed to Redis bus events")

            # Listen for messages
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data']

                    # Parse and route to appropriate handler
                    import json
                    try:
                        data_dict = json.loads(data)
                        await self._handle_redis_event(channel, data_dict)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse Redis message", channel=channel)

        except Exception as e:
            logger.error("Redis subscription failed", error=str(e))

    async def _handle_redis_event(self, channel: str, data: Dict[str, Any]):
        """Handle Redis bus event"""
        if channel == 'signals':
            await self.notify_signal_generated(data)
        elif channel == 'orders':
            status = data.get('status')
            if status == 'PLACED':
                await self.notify_order_placed(data)
            elif status == 'COMPLETE':
                await self.notify_order_filled(data)
            elif status == 'REJECTED':
                await self.notify_order_rejected(data)
        elif channel == 'positions':
            if data.get('event') == 'CLOSED':
                await self.notify_position_closed(data)
        elif channel == 'risk_alerts':
            await self.notify_risk_alert(
                data.get('alert_type', 'UNKNOWN'),
                data.get('message', '')
            )
        elif channel == 'system_errors':
            await self.notify_system_error(
                data.get('error_type', 'UNKNOWN'),
                data.get('error_message', '')
            )

    # ========================================
    # Polling Mode (Fallback)
    # ========================================

    async def poll_system_status(self, interval_seconds: int = 60):
        """Poll system status periodically (fallback if Redis not available)"""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    # Check market data connection
                    async with session.get(f"{self.api_url}/state") as resp:
                        state = await resp.json()

                    # Check if marketdata disconnected
                    if not state.get('marketdata_connected'):
                        await self.notify_marketdata_disconnected()

                    # Check daily PnL
                    async with session.get(f"{self.api_url}/risk") as resp:
                        risk = await resp.json()

                    daily_pnl = risk.get('daily_pnl', 0)
                    daily_loss_limit = risk.get('daily_loss_limit', 25000)

                    # Alert if approaching loss limit
                    if daily_pnl < -daily_loss_limit * 0.8:
                        await self.notify_risk_alert(
                            "DAILY_LOSS_APPROACHING",
                            f"PnL: ₹{daily_pnl:,.2f} (80% of limit)"
                        )

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error("Polling failed", error=str(e))
                await asyncio.sleep(interval_seconds)

    # ========================================
    # Main Entry Point
    # ========================================

    async def start(self, use_redis: bool = True, polling_enabled: bool = True):
        """Start Telegram bot"""
        logger.info("Starting Telegram bot", chat_id=self.chat_id)

        # Send startup notification
        await self.send_notification(
            "🤖 *Trading Bot Started*\n\n"
            "I'm now monitoring your trades.\n"
            "Use /help to see available commands."
        )

        # Start command handler
        asyncio.create_task(self.application.run_polling())

        # Start Redis subscriber (if enabled)
        if use_redis:
            asyncio.create_task(self.subscribe_to_events())

        # Start polling (if enabled)
        if polling_enabled:
            asyncio.create_task(self.poll_system_status(interval_seconds=60))

        logger.info("Telegram bot started successfully")


# ========================================
# Standalone Runner
# ========================================

async def main():
    """Run Telegram bot standalone"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables")
        return

    bot = TradingTelegramBot(
        bot_token=bot_token,
        chat_id=chat_id,
        api_url="http://localhost:8000"
    )

    await bot.start(use_redis=True, polling_enabled=True)

    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
