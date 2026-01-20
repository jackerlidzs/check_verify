"""
ChatGPT Auto-Login Script

Logs into ChatGPT accounts and extracts:
- Access token
- Session token (cookies)
- Saves to chatgpt_accounts.json
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
import json
import time
import re

os.chdir(Path(__file__).parent)

# Paths
ACCOUNTS_FILE = Path("app/core/data/chatgpt_accounts.json")
SESSIONS_DIR = Path("app/core/data/sessions")

# URLs
CHATGPT_LOGIN_URL = "https://chatgpt.com/"
CHATGPT_AUTH_URL = "https://auth.openai.com/"
K12_VERIFY_URL = "https://chatgpt.com/k12-verification"


def load_accounts():
    """Load accounts from JSON file."""
    if not ACCOUNTS_FILE.exists():
        return {"accounts": [], "config": {}}
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_accounts(data):
    """Save accounts to JSON file."""
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def login_account(email: str, password: str, headless: bool = False):
    """Login to ChatGPT and extract tokens.
    
    Args:
        email: ChatGPT account email
        password: ChatGPT account password
        headless: Run browser in headless mode
        
    Returns:
        dict with tokens and cookies, or None if failed
    """
    from playwright.sync_api import sync_playwright
    
    print(f"\n{'='*60}")
    print(f"🔐 Logging in: {email}")
    print(f"{'='*60}")
    
    result = {
        "access_token": "",
        "session_token": "",
        "cookies": [],
        "success": False,
        "error": None
    }
    
    with sync_playwright() as p:
        # Create session directory
        SESSIONS_DIR.mkdir(exist_ok=True)
        session_file = SESSIONS_DIR / f"{email.replace('@', '_at_').replace('.', '_')}.json"
        
        # Launch browser
        browser = p.chromium.launch(headless=headless)
        
        # Try to use existing session
        if session_file.exists():
            print(f"  📂 Loading saved session...")
            context = browser.new_context(storage_state=str(session_file))
        else:
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'
            )
        
        page = context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Navigate to ChatGPT
            print(f"  📍 Navigating to ChatGPT...")
            page.goto(CHATGPT_LOGIN_URL, wait_until='networkidle')
            time.sleep(2)
            
            # Check if already logged in
            if "chat" in page.url.lower() or page.locator('button:has-text("New chat")').count() > 0:
                print(f"  ✅ Already logged in!")
            else:
                # Click Login button
                print(f"  🔑 Starting login flow...")
                
                login_btn = page.locator('button:has-text("Log in"), a:has-text("Log in")')
                if login_btn.count() > 0:
                    login_btn.first.click()
                    time.sleep(3)
                
                # Wait for auth page
                page.wait_for_url("**/auth**", timeout=30000)
                
                # Enter email
                print(f"  📧 Entering email...")
                email_input = page.locator('input[name="email"], input[type="email"], input#email')
                if email_input.count() > 0:
                    email_input.first.fill(email)
                    time.sleep(0.5)
                    
                    # Click continue
                    continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
                    if continue_btn.count() > 0:
                        continue_btn.first.click()
                        time.sleep(2)
                
                # Enter password
                print(f"  🔒 Entering password...")
                password_input = page.locator('input[name="password"], input[type="password"]')
                if password_input.count() > 0:
                    password_input.first.fill(password)
                    time.sleep(0.5)
                    
                    # Click login
                    login_submit = page.locator('button:has-text("Continue"), button[type="submit"]')
                    if login_submit.count() > 0:
                        login_submit.first.click()
                        time.sleep(5)
                
                # Wait for redirect to ChatGPT
                print(f"  ⏳ Waiting for login complete...")
                try:
                    page.wait_for_url("**/chat**", timeout=60000)
                    print(f"  ✅ Login successful!")
                except:
                    # Check if stuck on verification
                    if "verify" in page.url.lower():
                        print(f"  ⚠️ Verification required - check email")
                        result["error"] = "Email verification required"
                        return result
                    else:
                        print(f"  ❌ Login may have failed")
            
            # Save session
            print(f"  💾 Saving session...")
            context.storage_state(path=str(session_file))
            
            # Extract cookies
            cookies = context.cookies()
            result["cookies"] = cookies
            
            # Find session token
            for cookie in cookies:
                if cookie["name"] == "__Secure-next-auth.session-token":
                    result["session_token"] = cookie["value"]
                    print(f"  ✓ Session token found")
                    break
            
            # Try to get access token from API call
            print(f"  🔍 Looking for access token...")
            
            # Navigate to session endpoint to get token
            try:
                page.goto("https://chatgpt.com/api/auth/session", wait_until='networkidle')
                time.sleep(1)
                
                # Get page content (JSON)
                content = page.inner_text('body')
                if content:
                    try:
                        session_data = json.loads(content)
                        if "accessToken" in session_data:
                            result["access_token"] = session_data["accessToken"]
                            print(f"  ✓ Access token found")
                    except:
                        pass
            except:
                pass
            
            # Navigate to K12 verification page
            print(f"  📍 Navigating to K12 verification...")
            page.goto(K12_VERIFY_URL, wait_until='networkidle')
            time.sleep(2)
            
            # Get current URL (should have verification link)
            current_url = page.url
            print(f"  🔗 URL: {current_url}")
            
            # Check for Verify button
            verify_btn = page.locator('button:has-text("Verify"), a:has-text("Verify")')
            if verify_btn.count() > 0:
                print(f"  ✓ Verify button found")
            
            result["success"] = True
            result["k12_url"] = current_url
            
            # Take screenshot
            screenshot_path = SESSIONS_DIR / f"{email.split('@')[0]}_login.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  📸 Screenshot saved: {screenshot_path.name}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            
            # Take error screenshot
            try:
                screenshot_path = SESSIONS_DIR / f"{email.split('@')[0]}_error.png"
                page.screenshot(path=str(screenshot_path))
            except:
                pass
            
        finally:
            browser.close()
    
    return result


def login_all_accounts(headless: bool = False):
    """Login to all accounts and update tokens."""
    data = load_accounts()
    
    if not data.get("accounts"):
        print("❌ No accounts found in chatgpt_accounts.json")
        print("   Please add accounts first.")
        return
    
    print("="*60)
    print("🔐 ChatGPT Multi-Account Login")
    print("="*60)
    print(f"Accounts to process: {len(data['accounts'])}")
    
    for i, account in enumerate(data["accounts"]):
        email = account.get("email", "")
        password = account.get("password", "")
        
        if not email or not password:
            print(f"\n[{i+1}] ⚠️ Skipping - missing email/password")
            continue
        
        result = login_account(email, password, headless)
        
        if result["success"]:
            # Update account data
            account["access_token"] = result.get("access_token", "")
            account["session_token"] = result.get("session_token", "")
            account["cookies"] = result.get("cookies", [])
            account["last_used"] = datetime.now().isoformat()
            account["status"] = "active"
            print(f"\n✅ Account {i+1} updated successfully")
        else:
            account["status"] = "error"
            account["notes"] = result.get("error", "Login failed")
            print(f"\n❌ Account {i+1} failed: {result.get('error')}")
        
        # Save after each account
        save_accounts(data)
        
        # Delay between accounts
        if i < len(data["accounts"]) - 1:
            print("\n⏳ Waiting 5 seconds before next account...")
            time.sleep(5)
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    active = sum(1 for a in data["accounts"] if a.get("status") == "active")
    print(f"✅ Active accounts: {active}/{len(data['accounts'])}")
    print(f"💾 Saved to: {ACCOUNTS_FILE}")


def login_single(email: str, password: str):
    """Login a single account and save."""
    data = load_accounts()
    
    # Check if account exists
    existing = next((a for a in data["accounts"] if a["email"] == email), None)
    
    result = login_account(email, password, headless=False)
    
    if result["success"]:
        account_data = {
            "id": f"account_{len(data['accounts']) + 1}",
            "email": email,
            "password": password,
            "access_token": result.get("access_token", ""),
            "session_token": result.get("session_token", ""),
            "cookies": result.get("cookies", []),
            "status": "active",
            "last_used": datetime.now().isoformat(),
            "verified_k12": False,
            "notes": ""
        }
        
        if existing:
            # Update existing
            idx = data["accounts"].index(existing)
            data["accounts"][idx].update(account_data)
        else:
            # Add new
            data["accounts"].append(account_data)
        
        save_accounts(data)
        print(f"\n✅ Account saved to {ACCOUNTS_FILE}")
        return True
    
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ChatGPT Account Login')
    parser.add_argument('--all', action='store_true', help='Login all accounts from JSON')
    parser.add_argument('--email', type=str, help='Single account email')
    parser.add_argument('--password', type=str, help='Single account password')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    
    args = parser.parse_args()
    
    if args.all:
        login_all_accounts(args.headless)
    elif args.email and args.password:
        login_single(args.email, args.password)
    else:
        print("Usage:")
        print("  python chatgpt_login.py --all                    # Login all accounts")
        print("  python chatgpt_login.py --email X --password Y   # Login single account")
        print("  python chatgpt_login.py --all --headless         # Headless mode")
