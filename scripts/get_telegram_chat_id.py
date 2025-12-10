#!/usr/bin/env python3
"""
Get your Telegram Chat ID

This script will:
1. Connect to your bot
2. Tell you to send a message
3. Retrieve your chat ID
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def get_chat_id():
    """Get chat ID by checking for messages"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return

    try:
        from telegram import Bot

        bot = Bot(token=BOT_TOKEN)

        print("\n" + "=" * 60)
        print("  GET YOUR TELEGRAM CHAT ID")
        print("=" * 60)
        print()

        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")
        print(f"   Bot name: {bot_info.first_name}")
        print()

        print("📱 STEP 1: Open Telegram and find your bot")
        print(f"   Search for: @{bot_info.username}")
        print()
        print("📱 STEP 2: Start a chat with your bot")
        print("   Send any message (e.g., 'hello')")
        print()
        print("⏳ Waiting for your message...")
        print("   (This script will check for 60 seconds)")
        print()

        # Poll for updates
        for i in range(60):
            updates = await bot.get_updates()

            if updates:
                # Get the latest update with a message
                for update in updates:
                    if update.message:
                        chat_id = update.message.chat.id
                        username = update.message.from_user.username or "N/A"
                        first_name = update.message.from_user.first_name or "N/A"

                        print("\n" + "=" * 60)
                        print("  ✅ CHAT ID FOUND!")
                        print("=" * 60)
                        print()
                        print(f"Your Chat ID: {chat_id}")
                        print(f"Username: @{username}")
                        print(f"Name: {first_name}")
                        print()
                        print("=" * 60)
                        print()
                        print("📝 Add this to your .env file:")
                        print(f'   TELEGRAM_CHAT_ID="{chat_id}"')
                        print()
                        print("Then run: python scripts/test_telegram_bot.py")
                        print()

                        # Send confirmation message
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"✅ *Chat ID Found!*\n\n"
                                 f"Your Chat ID: `{chat_id}`\n\n"
                                 f"Add this to your `.env` file and run the test script.",
                            parse_mode='Markdown'
                        )

                        return

            await asyncio.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"   Still waiting... ({i + 1}/60 seconds)")

        print("\n⏰ Timed out waiting for message")
        print("   Make sure you:")
        print(f"   1. Searched for @{bot_info.username} in Telegram")
        print("   2. Clicked START or sent a message")
        print("   3. Run this script again")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nCheck:")
        print("1. Bot token is correct")
        print("2. You have internet connection")
        print("3. pip install python-telegram-bot is installed")


if __name__ == "__main__":
    asyncio.run(get_chat_id())
