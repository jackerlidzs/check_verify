"""
Test Telegram Bot Connection

Quick test to verify Telegram API works and can interact with @bjfreemail_bot
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
import json
import os
import re

os.chdir(Path(__file__).parent)

# Load config
CONFIG_FILE = Path("app/core/data/signup_config.json")

async def test_telegram():
    from telethon import TelegramClient
    
    # Load config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    api_id = config["telegram"]["api_id"]
    api_hash = config["telegram"]["api_hash"]
    bot_username = config["telegram"]["bot_username"]
    
    print("="*60)
    print("🔌 Testing Telegram Connection")
    print("="*60)
    print(f"API ID: {api_id}")
    print(f"Bot: @{bot_username}")
    
    # Create session - use absolute path
    session_file = Path(__file__).parent / "app" / "core" / "data" / "telegram_session"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    client = TelegramClient(str(session_file), api_id, api_hash)
    
    try:
        print("\n📱 Connecting to Telegram...")
        print("   (First time will ask for phone number + code)")
        await client.start()
        
        me = await client.get_me()
        print(f"\n✅ Connected as: {me.first_name} (@{me.username})")
        
        # Test sending message to bot
        print(f"\n📤 Sending /start to @{bot_username}...")
        await client.send_message(bot_username, "/start")
        
        # Wait for response
        print("⏳ Waiting for response...")
        await asyncio.sleep(3)
        
        # Read messages
        print(f"\n📬 Recent messages from @{bot_username}:")
        async for msg in client.iter_messages(bot_username, limit=3):
            if msg.text:
                print(f"\n  [{msg.date}]")
                print(f"  {msg.text[:200]}...")
        
        # Test getting new email
        print(f"\n📧 Testing /new command...")
        await client.send_message(bot_username, "/new")
        await asyncio.sleep(3)
        
        # Read email response
        async for msg in client.iter_messages(bot_username, limit=2):
            if msg.text and "@" in msg.text:
                # Find email address
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                if email_match:
                    print(f"\n✅ Got temp email: {email_match.group()}")
                    break
        
        print("\n" + "="*60)
        print("✅ Telegram test PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_telegram())
