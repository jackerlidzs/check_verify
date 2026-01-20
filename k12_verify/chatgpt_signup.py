"""
ChatGPT Signup v4 - With Playwright Stealth

Uses playwright-stealth to avoid bot detection.
No captcha needed - just stealth mode.
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
SESSIONS_DIR = Path("app/core/data/sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_account(email, password):
    accounts = json.load(open(ACCOUNTS_FILE)) if ACCOUNTS_FILE.exists() else {"accounts": []}
    accounts["accounts"].append({
        "email": email,
        "password": password,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    })
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    print(f"  💾 Account saved!")


def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))


class TelegramEmailManager:
    def __init__(self, api_id, api_hash, bot_username="bjfreemail_bot"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_username = bot_username
        self.client = None
    
    async def connect(self):
        from telethon import TelegramClient
        self.client = TelegramClient(str(SESSION_FILE), self.api_id, self.api_hash)
        await self.client.start()
        me = await self.client.get_me()
        print(f"✅ Telegram connected as {me.username}")
    
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
    
    async def get_new_email(self):
        await self.client.send_message(self.bot_username, "/new")
        await asyncio.sleep(3)
        
        async for msg in self.client.iter_messages(self.bot_username, limit=5):
            if msg.text and "创建地址成功" in msg.text:
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                if match:
                    return match.group()
            elif msg.text and "达上限" in msg.text:
                print("  ⚠️ Email limit! Cleaning...")
                await self.cleanup_all_emails()
                return await self.get_new_email()
        return None
    
    async def delete_email(self, email):
        print(f"  🗑️ Deleting: {email}")
        await self.client.send_message(self.bot_username, f"/delete {email}")
        await asyncio.sleep(2)
    
    async def get_email_list(self):
        await self.client.send_message(self.bot_username, "/address")
        await asyncio.sleep(2)
        emails = []
        async for msg in self.client.iter_messages(self.bot_username, limit=3):
            if msg.text:
                matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                emails.extend(matches)
        return list(set(emails))
    
    async def cleanup_all_emails(self):
        print("  🧹 Cleaning all emails...")
        emails = await self.get_email_list()
        for email in emails:
            await self.delete_email(email)
            await asyncio.sleep(1)
    
    async def wait_for_verification(self, timeout=120):
        print(f"  ⏳ Watching for verification code...")
        start = time.time()
        checked = set()
        
        while time.time() - start < timeout:
            async for msg in self.client.iter_messages(self.bot_username, limit=15):
                if msg.id in checked:
                    continue
                checked.add(msg.id)
                
                if msg.text and ("openai" in msg.text.lower() or "chatgpt" in msg.text.lower() or "verify" in msg.text.lower()):
                    code_match = re.search(r'\b(\d{6})\b', msg.text)
                    if code_match:
                        return {"type": "code", "value": code_match.group(1)}
                    link_match = re.search(r'https://[^\s<>"]+', msg.text)
                    if link_match:
                        return {"type": "link", "value": link_match.group()}
            await asyncio.sleep(5)
        return None


async def signup_with_stealth(email, password, proxy_config):
    """Browser signup with stealth mode."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    
    result = {"success": False, "needs_verification": False, "error": None}
    safe_email = email.split('@')[0]
    
    print(f"\n  📝 Starting signup for: {email}")
    print(f"  🔒 Using Stealth Mode")
    
    async with async_playwright() as p:
        # Setup proxy
        proxy = None
        if proxy_config.get("host"):
            proxy = {
                "server": f"http://{proxy_config['host']}:{proxy_config['rotating_port']}",
                "username": proxy_config.get("user", ""),
                "password": proxy_config.get("pass", "")
            }
            print(f"  🌐 Proxy: {proxy_config['host']}:{proxy_config['rotating_port']}")
        
        # Launch browser with stealth
        stealth = Stealth()
        browser = await p.chromium.launch(
            headless=False, 
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Apply stealth to context
        await stealth.apply_stealth_async(context)
        
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Check IP
            try:
                await page.goto("https://api.ipify.org?format=json", timeout=15000)
                ip = json.loads(await page.inner_text("body")).get("ip", "?")
                print(f"  🌐 IP: {ip}")
            except:
                pass
            
            # Step 1: Go to ChatGPT
            print(f"  📍 Step 1: Opening chatgpt.com...")
            await page.goto("https://chatgpt.com/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            print(f"  📍 URL: {page.url}")
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_1_home.png"))
            
            # Step 2: Find and click Sign up button
            print(f"  📍 Step 2: Looking for Sign Up button...")
            
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # Try multiple selectors
            clicked = False
            selectors = [
                'text="Sign up for free"', 
                'text="Sign up"',
                'button >> text="Sign up"',
                'a >> text="Sign up"',
                '[data-testid="signup-button"]',
                'button:has-text("Sign up")',
                'a:has-text("Sign up")',
            ]
            
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        print(f"  ✓ Found: {sel}")
                        # Click and wait for navigation
                        async with page.expect_navigation(timeout=15000):
                            await loc.first.click()
                        clicked = True
                        print(f"  ✓ Navigation complete")
                        break
                except Exception as e:
                    # If navigation didn't happen, still try the click
                    try:
                        await loc.first.click()
                        clicked = True
                        await asyncio.sleep(5)
                        break
                    except:
                        continue
            
            if not clicked:
                # Try JavaScript click
                print(f"  ⚠️ Button selectors failed, trying JS...")
                try:
                    await page.evaluate('''
                        const btns = Array.from(document.querySelectorAll('button, a'));
                        const signup = btns.find(b => b.textContent.toLowerCase().includes('sign up'));
                        if (signup) signup.click();
                    ''')
                    clicked = True
                    await asyncio.sleep(4)
                except:
                    pass
            
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_2_after_signup.png"))
            print(f"  📍 URL after signup click: {page.url}")
            
            # Step 3: Wait for modal/auth form to appear
            print(f"  📍 Step 3: Waiting for auth modal...")
            
            # Wait for email input to appear (could be in modal or iframe)
            email_found = False
            
            # Check for iframe (auth might be in iframe)
            iframes = page.frame_locator('iframe')
            
            # Try different approaches to find email input
            for attempt in range(5):  # Try up to 5 times
                await asyncio.sleep(2)
                
                # First try on main page
                email_input = page.locator('input[type="email"], input[name="email"], input[id*="email"], input[placeholder*="email" i]')
                count = await email_input.count()
                if count > 0:
                    print(f"  ✓ Found email input on page (count={count})")
                    email_found = True
                    break
                
                # Check inside any modals/dialogs
                modal_selectors = [
                    '[role="dialog"]',
                    '.modal',
                    '[class*="modal"]',
                    '[class*="overlay"]',
                    '[class*="auth"]',
                ]
                
                for modal_sel in modal_selectors:
                    try:
                        modal = page.locator(modal_sel)
                        if await modal.count() > 0:
                            modal_email = modal.locator('input[type="email"], input[name="email"]')
                            if await modal_email.count() > 0:
                                email_input = modal_email
                                email_found = True
                                print(f"  ✓ Found email in modal: {modal_sel}")
                                break
                    except:
                        continue
                
                if email_found:
                    break
                    
                print(f"  ⏳ Waiting for form... (attempt {attempt+1}/5)")
            
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_3_modal.png"))
            
            # Step 4: Enter email
            print(f"  📍 Step 4: Entering email...")
            
            if email_found and await email_input.count() > 0:
                await email_input.first.click()
                await asyncio.sleep(0.5)
                await email_input.first.fill(email)
                print(f"  ✓ Email entered: {email}")
                await asyncio.sleep(1)
                
                # Click Continue - be specific to avoid OAuth buttons
                # Try exact "Continue" text, not "Continue with Google" etc.
                continue_selectors = [
                    'button:text-is("Continue")',  # Exact match
                    'button[type="submit"]:has-text("Continue"):not(:has-text("with"))',
                    'button:has-text("Continue"):not(:has-text("Google")):not(:has-text("Microsoft")):not(:has-text("Apple"))',
                    'form button[type="submit"]',
                    'button[type="submit"]',
                ]
                
                clicked = False
                for sel in continue_selectors:
                    try:
                        btn = page.locator(sel)
                        if await btn.count() > 0:
                            print(f"  ✓ Clicking: {sel}")
                            await btn.first.click()
                            clicked = True
                            await asyncio.sleep(4)
                            break
                    except:
                        continue
                
                if not clicked:
                    print(f"  ⚠️ Continue button not found - trying keyboard Enter")
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(4)
            else:
                print(f"  ❌ Email input not found!")
                result["error"] = "Email input not found"
                await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_error_no_email.png"))
                return result
            
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_4_after_email.png"))
            
            # Step 5: Enter password
            print(f"  📍 Step 5: Waiting for password field...")
            
            # Wait for visible password input (not hidden)
            password_found = False
            for attempt in range(10):
                await asyncio.sleep(2)
                
                # Only look for visible password inputs
                password_input = page.locator('input[type="password"]:visible')
                if await password_input.count() > 0:
                    password_found = True
                    print(f"  ✓ Found visible password input")
                    break
                    
                print(f"  ⏳ Waiting for password field... (attempt {attempt+1}/10)")
            
            if password_found:
                await password_input.first.fill(password)
                print(f"  ✓ Password entered")
                await asyncio.sleep(1)
                
                # Click Continue - use same careful selection
                continue_selectors = [
                    'button:text-is("Continue")',
                    'button[type="submit"]',
                ]
                for sel in continue_selectors:
                    try:
                        btn = page.locator(sel)
                        if await btn.count() > 0:
                            print(f"  ✓ Clicking password Continue: {sel}")
                            await btn.first.click()
                            await asyncio.sleep(5)
                            break
                    except:
                        continue
            else:
                print(f"  ⚠️ Password field not found - may need manual entry")
            
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_5_after_pass.png"))
            
            # Step 6: Check result
            print(f"  📍 Step 6: Checking result...")
            await asyncio.sleep(3)
            
            current_url = page.url.lower()
            page_text = (await page.inner_text('body')).lower()
            
            print(f"  📍 Final URL: {page.url}")
            await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_6_final.png"))
            
            # Check for verification required
            if any(x in page_text for x in ["verify your email", "check your email", "verification", "sent", "inbox"]):
                print(f"  📬 Email verification required!")
                result["needs_verification"] = True
            elif "create-account" in current_url:
                print(f"  📬 Still on create-account - may need email verification")
                result["needs_verification"] = True
            elif "chat" in current_url and "auth" not in current_url:
                print(f"  🎉 Signup successful!")
                result["success"] = True
            elif "error" in current_url:
                print(f"  ❌ Auth error")
                result["error"] = "Auth error"
            else:
                print(f"  ⚠️ Unknown state - check screenshots")
            
            # Keep open to see
            print(f"  ⏳ Browser open for 15s...")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            result["error"] = str(e)
            try:
                await page.screenshot(path=str(SESSIONS_DIR / f"{safe_email}_error.png"))
            except:
                pass
        finally:
            await browser.close()
    
    return result


async def run_signup(num_accounts=1):
    config = load_config()
    
    print("="*60)
    print("🚀 ChatGPT Signup v4 (Stealth Mode)")
    print("="*60)
    print(f"Accounts: {num_accounts}")
    
    telegram = TelegramEmailManager(
        config["telegram"]["api_id"],
        config["telegram"]["api_hash"],
        config["telegram"]["bot_username"]
    )
    
    await telegram.connect()
    
    # Cleanup if needed
    current = await telegram.get_email_list()
    if len(current) >= 4:
        await telegram.cleanup_all_emails()
    
    created = 0
    
    for i in range(num_accounts):
        print(f"\n{'='*60}")
        print(f"📝 Account {i+1}/{num_accounts}")
        print(f"{'='*60}")
        
        email = await telegram.get_new_email()
        if not email:
            print("  ❌ No email")
            continue
        print(f"  ✓ Email: {email}")
        
        password = config["signup"].get("password") or generate_password()
        print(f"  ✓ Password: {password}")
        
        result = await signup_with_stealth(email, password, config["proxy"])
        
        if result.get("needs_verification"):
            print(f"  📬 Waiting for verification email...")
            verification = await telegram.wait_for_verification(timeout=180)
            if verification:
                print(f"  ✅ Got: {verification['type']} = {verification['value'][:60]}...")
                # For now ask user to confirm
                print(f"\n  👤 Please complete verification manually if needed")
                confirm = input("  Signup complete? (y/n): ")
                if confirm.lower() == 'y':
                    result["success"] = True
        
        if result.get("success"):
            save_account(email, password)
            created += 1
        
        await telegram.delete_email(email)
        
        if i < num_accounts - 1:
            await asyncio.sleep(10)
    
    await telegram.disconnect()
    
    print(f"\n{'='*60}")
    print(f"📊 Created: {created}/{num_accounts}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--num', type=int, default=1)
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    
    if args.cleanup:
        async def cleanup():
            config = load_config()
            t = TelegramEmailManager(config["telegram"]["api_id"], config["telegram"]["api_hash"])
            await t.connect()
            await t.cleanup_all_emails()
            await t.disconnect()
        asyncio.run(cleanup())
    else:
        asyncio.run(run_signup(args.num))
