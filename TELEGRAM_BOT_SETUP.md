# 📱 Telegram Bot Setup Guide

Get real-time trading updates on your phone!

---

## **1. Create Telegram Bot**

### **Step 1: Open Telegram**
- Search for `@BotFather` (official Telegram bot creator)
- Start a chat

### **Step 2: Create New Bot**
```
/newbot
```

### **Step 3: Name Your Bot**
```
Bot name: AITRAPP Trading Bot
Bot username: aitrapp_trading_bot (must be unique)
```

### **Step 4: Save Bot Token**
BotFather will give you a token like:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
```

**⚠️ KEEP THIS SECRET!** This is your bot's password.

---

## **2. Get Your Chat ID**

### **Step 1: Start Chat with Your Bot**
- Search for your bot username in Telegram
- Click START

### **Step 2: Get Chat ID**

**Option A: Use GetIDsBot**
1. Search for `@getidsbot` in Telegram
2. Start chat
3. It will send you your chat ID (e.g., `123456789`)

**Option B: Use API**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in the response

---

## **3. Configure Environment Variables**

### **Create `.env` file** (if not exists):
```bash
# In /Users/mac/CRYPTO/AITRAPP/.env
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
TELEGRAM_CHAT_ID="123456789"
```

### **Or export directly:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

---

## **4. Install Dependencies**

```bash
cd /Users/mac/CRYPTO/AITRAPP

# Install Telegram bot library
pip install python-telegram-bot aiohttp redis python-dotenv

# Or add to requirements.txt
echo "python-telegram-bot==20.7" >> requirements.txt
echo "aiohttp==3.9.1" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt
pip install -r requirements.txt
```

---

## **5. Start Bot**

### **Standalone Mode** (separate process):
```bash
python -m packages.integrations.telegram_bot
```

### **Integrated Mode** (within main app):
Add to `apps/api/main.py`:
```python
from packages.integrations.telegram_bot import TradingTelegramBot
import os

# In startup event
@app.on_event("startup")
async def start_telegram_bot():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if bot_token and chat_id:
        telegram_bot = TradingTelegramBot(
            bot_token=bot_token,
            chat_id=chat_id,
            api_url="http://localhost:8000"
        )
        await telegram_bot.start(use_redis=True, polling_enabled=True)
```

---

## **6. Test Bot**

### **Send Test Message:**
```bash
python3 << 'EOF'
import asyncio
from telegram import Bot

async def test_bot():
    bot = Bot(token="YOUR_BOT_TOKEN")
    await bot.send_message(
        chat_id="YOUR_CHAT_ID",
        text="🤖 Test message from AITRAPP!"
    )

asyncio.run(test_bot())
EOF
```

You should receive a message on Telegram!

---

## **7. Available Commands**

Once bot is running, send these commands in Telegram:

```
/start - Activate bot
/status - System status (mode, marketdata, positions)
/pnl - Daily PnL and loss limit
/positions - Open positions with PnL
/signals - OptionsRanker signal generation today
/risk - Risk metrics (margin, heat, limits)
/metrics - Full observability summary
/help - Show all commands
```

---

## **8. Real-Time Notifications**

Bot will automatically send notifications for:

### **Signal Generation**
```
🎯 Signal Generated

Strategy: OptionsRanker
Symbol: NIFTY
Side: LONG
Confidence: 78%

Waiting for risk approval...
```

### **Order Execution**
```
📤 Order Placed

Symbol: NIFTY 24800 CE
Side: BUY
Qty: 50
Price: ₹125.50
Order ID: 240319000012345
```

### **Position Updates**
```
🟢 Position Closed

Symbol: NIFTY 24800 CE
Exit Reason: TAKE_PROFIT
PnL: ₹3,250

Position flattened ✅
```

### **Risk Alerts**
```
🚨 RISK ALERT

Type: DAILY_LOSS_APPROACHING
Message: PnL: ₹-20,000 (80% of limit)

Check system immediately!
```

### **System Errors**
```
❌ System Error

Type: MARKETDATA_DISCONNECTED
Error: WebSocket connection lost

Check logs for details
```

---

## **9. Notification Modes**

### **Mode 1: Redis Bus (Real-Time)**
- Subscribes to Redis pub/sub channels
- Instant notifications (<1 second latency)
- Requires Redis running

### **Mode 2: Polling (Fallback)**
- Checks API every 60 seconds
- Slightly delayed notifications
- Works without Redis

### **Mode 3: Hybrid (Recommended)**
- Uses Redis for real-time events
- Polls for status checks
- Best of both worlds

---

## **10. Customization**

### **Change Notification Frequency:**
```python
# In telegram_bot.py
await bot.poll_system_status(interval_seconds=30)  # Poll every 30 seconds
```

### **Filter Notifications:**
```python
# Only notify for large PnL changes
if abs(pnl) > 5000:  # Only if PnL > ₹5,000
    await bot.notify_daily_pnl_update(pnl, limit)
```

### **Add Custom Commands:**
```python
async def cmd_custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /custom command"""
    await update.message.reply_text("Custom response")

# Register in __init__
self.application.add_handler(CommandHandler("custom", self.cmd_custom))
```

---

## **11. Security Best Practices**

1. **Never share bot token** - It's like a password
2. **Whitelist your chat ID** - Only respond to your messages
3. **Use environment variables** - Don't hardcode tokens
4. **Enable HTTPS** - For webhook mode (optional)
5. **Rotate tokens periodically** - Via BotFather

---

## **12. Troubleshooting**

### **Bot not responding:**
```bash
# Check if bot is running
ps aux | grep telegram_bot

# Check logs
tail -f logs/telegram_bot.log

# Test bot token
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

### **Not receiving notifications:**
```bash
# Verify chat ID
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"

# Test send message
python -m packages.integrations.telegram_bot
```

### **Redis connection failed:**
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Start Redis
redis-server
```

---

## **13. Production Deployment**

### **Run as systemd service:**
```bash
# Create service file
sudo nano /etc/systemd/system/aitrapp-telegram.service
```

```ini
[Unit]
Description=AITRAPP Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/Users/mac/CRYPTO/AITRAPP
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 -m packages.integrations.telegram_bot
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable aitrapp-telegram
sudo systemctl start aitrapp-telegram

# Check status
sudo systemctl status aitrapp-telegram
```

---

## **14. Next Steps**

✅ Bot created and configured
✅ Environment variables set
✅ Dependencies installed
✅ Bot tested

**Now:** Start your trading system and bot together:

```bash
# Terminal 1: Trading system
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Telegram bot
python -m packages.integrations.telegram_bot
```

You'll receive a startup message on Telegram:
```
🤖 Trading Bot Started

I'm now monitoring your trades.
Use /help to see available commands.
```

**Happy trading! 📈**
