"""
Simple ChatGPT Signup - Step by step with user interaction.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
import json
import time
import re
import asyncio
import random
import string

os.chdir(Path(__file__).parent)

# Paths
ACCOUNTS_FILE = Path("app/core/data/chatgpt_accounts.json")
CONFIG_FILE = Path("app/core/data/signup_config.json")
SESSION_FILE = Path(__file__).parent / "app" / "core" / "data" / "telegram_session"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))


async def get_telegram_email(api_id, api_hash, bot_username):
    """Get temp email from Telegram bot."""
    from telethon import TelegramClient
    
    client = TelegramClient(str(SESSION_FILE), api_id, api_hash)
    await client.start()
    
    print(f"✅ Telegram connected as {(await client.get_me()).username}")
    
    # First send /start
    print("📧 Sending /start to bot...")
    await client.send_message(bot_username, "/start")
    await asyncio.sleep(2)
    
    # Then send /new
    print("📧 Requesting new email with /new...")
    await client.send_message(bot_username, "/new")
    await asyncio.sleep(5)  # Wait longer for response
    
    # Read response - look for email pattern
    email = None
    print("📬 Reading bot messages...")
    async for msg in client.iter_messages(bot_username, limit=10):
        if msg.text:
            print(f"   Message: {msg.text[:50]}...")
            if "@" in msg.text:
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                if match:
                    email = match.group()
                    print(f"   Found email: {email}")
                    break
    
    await client.disconnect()
    return email


def signup_with_browser(email, password, proxy_config):
    """Open browser for manual signup assistance."""
    from playwright.sync_api import sync_playwright
    
    print(f"\n{'='*60}")
    print(f"📝 Starting signup for: {email}")
    print(f"🔒 Password: {password}")
    print(f"{'='*60}")
    
    with sync_playwright() as p:
        proxy = None
        if proxy_config.get("host"):
            proxy = {
                "server": f"http://{proxy_config['host']}:{proxy_config['rotating_port']}",
            }
            if proxy_config.get("user"):
                proxy["username"] = proxy_config["user"]
                proxy["password"] = proxy_config["pass"]
            print(f"🌐 Proxy: {proxy_config['host']}:{proxy_config['rotating_port']}")
        
        browser = p.chromium.launch(headless=False, proxy=proxy)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.set_default_timeout(120000)
        
        try:
            # Check IP
            print("🔍 Checking IP...")
            page.goto("https://api.ipify.org?format=json", timeout=15000)
            ip = json.loads(page.inner_text("body")).get("ip", "Unknown")
            print(f"🌐 Your IP: {ip}")
            
            # Go to ChatGPT
            print("\n📍 Opening ChatGPT signup...")
            page.goto("https://chat.openai.com/auth/login", wait_until='networkidle')
            time.sleep(2)
            
            # Auto-fill if possible
            signup_btn = page.locator('button:has-text("Sign up"), a:has-text("Sign up")')
            if signup_btn.count() > 0:
                signup_btn.first.click()
                time.sleep(3)
            
            email_input = page.locator('input[name="email"], input[type="email"]')
            if email_input.count() > 0:
                email_input.first.fill(email)
                print(f"✓ Email filled: {email}")
            
            print("\n" + "="*60)
            print("⏳ MANUAL STEPS:")
            print("1. Click Continue")
            print("2. Enter password: " + password)
            print("3. Complete signup")
            print("4. When done, press Enter here...")
            print("="*60)
            
            input("\n>>> Press Enter when signup is complete <<<")
            
            # Check if successful
            if "chat" in page.url.lower():
                print("\n🎉 Signup appears successful!")
                return True
            else:
                print(f"\n⚠️ Current URL: {page.url}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
            
        finally:
            input("\n>>> Press Enter to close browser <<<")
            browser.close()


async def get_email_and_password():
    """Get email from Telegram and generate password."""
    config = load_config()
    
    print("="*60)
    print("🚀 Simple ChatGPT Signup")
    print("="*60)
    
    # Get email from Telegram
    email = await get_telegram_email(
        config["telegram"]["api_id"],
        config["telegram"]["api_hash"],
        config["telegram"]["bot_username"]
    )
    
    if not email:
        print("❌ Failed to get temp email")
        return None, None, None
    
    print(f"✅ Got email: {email}")
    
    # Generate password
    password = config["signup"].get("password") or generate_password()
    print(f"✅ Password: {password}")
    
    return email, password, config


def main():
    """Main function - separates async and sync."""
    # Step 1: Get email (async)
    email, password, config = asyncio.run(get_email_and_password())
    
    if not email:
        return
    
    # Step 2: Open browser (sync - outside asyncio)
    success = signup_with_browser(email, password, config["proxy"])
    
    if success:
        # Save account
        accounts = json.load(open(ACCOUNTS_FILE)) if ACCOUNTS_FILE.exists() else {"accounts": []}
        accounts["accounts"].append({
            "email": email,
            "password": password,
            "created_at": datetime.now().isoformat()
        })
        with open(ACCOUNTS_FILE, "w") as f:
            json.dump(accounts, f, indent=2)
        print(f"\n💾 Account saved to {ACCOUNTS_FILE}")


if __name__ == "__main__":
    main()
