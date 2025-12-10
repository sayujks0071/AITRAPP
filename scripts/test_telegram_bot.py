#!/usr/bin/env python3
"""
Test Telegram Bot Integration

Quick test script to verify bot is working before connecting to trading system.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def test_send_message():
    """Test sending a message to Telegram"""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        print("\nSet them in .env file or export:")
        print('  export TELEGRAM_BOT_TOKEN="your_token"')
        print('  export TELEGRAM_CHAT_ID="your_chat_id"')
        sys.exit(1)

    try:
        from telegram import Bot

        bot = Bot(token=BOT_TOKEN)

        print("🔄 Testing bot connection...")

        # Test 1: Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")

        # Test 2: Send test message
        message = await bot.send_message(
            chat_id=CHAT_ID,
            text="🤖 *Test Message*\n\nAITRAPP Telegram bot is working!\n\nYou should see this message in your Telegram app.",
            parse_mode='Markdown'
        )
        print(f"✅ Message sent successfully (message_id: {message.message_id})")

        # Test 3: Send formatted message with emoji
        formatted_message = """
📊 *System Status Test*

Mode: `LIVE`
Status: `✅ Connected`
Market Data: `✅ Active`

This is a test of formatted messages.
"""
        await bot.send_message(
            chat_id=CHAT_ID,
            text=formatted_message,
            parse_mode='Markdown'
        )
        print("✅ Formatted message sent successfully")

        print("\n✅ All tests passed!")
        print(f"\nChat ID: {CHAT_ID}")
        print(f"Bot Username: @{bot_info.username}")
        print("\nYou should have received 2 test messages in Telegram.")
        print("\nNext step: Start the bot with:")
        print("  python -m packages.integrations.telegram_bot")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nCheck:")
        print("1. Bot token is correct (from @BotFather)")
        print("2. Chat ID is correct (from @getidsbot)")
        print("3. You've started a chat with your bot (/start)")
        sys.exit(1)


async def test_api_connection():
    """Test connection to trading API"""
    import aiohttp

    api_url = "http://localhost:8000"

    try:
        print(f"\n🔄 Testing API connection to {api_url}...")

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API connected: {data}")
                else:
                    print(f"⚠️ API returned status {resp.status}")

    except aiohttp.ClientConnectorError:
        print("⚠️ API not reachable (is uvicorn running?)")
        print("   Start with: python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"⚠️ API connection failed: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("  AITRAPP Telegram Bot Test Suite")
    print("=" * 60)

    # Test 1: Telegram bot
    await test_send_message()

    # Test 2: API connection (optional)
    await test_api_connection()

    print("\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
