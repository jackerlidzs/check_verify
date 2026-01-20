"""
ChatGPT Auth0 Signup - With Playwright Stealth & ISP Proxy
Combines reverse-engineered Auth0 flow with bot bypass technologies.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import re
import asyncio
import random
import string

# Import shared utilities
from utils import (
    load_config,
    generate_password,
    save_account,
    get_proxy_config,
    SCREENSHOTS_DIR,
)

# Load config
CONFIG = load_config()


async def signup_with_stealth_isp(email: str, password: str, use_proxy: bool = True):
    """
    ChatGPT signup using Playwright Stealth + ISP Proxy.
    """
    from playwright.async_api import async_playwright
    
    # Try to import stealth
    try:
        from playwright_stealth import Stealth
        has_stealth = True
    except ImportError:
        print("  ⚠️ playwright-stealth not installed, using basic stealth")
        has_stealth = False
    
    result = {
        "success": False,
        "needs_verification": False,
        "access_token": None,
        "error": None
    }
    
    safe_email = email.split('@')[0][:20]
    
    print(f"\n{'='*60}")
    print(f"  🎖️ ChatGPT Auth0 Signup (Stealth + ISP)")
    print(f"{'='*60}")
    print(f"  📧 Email: {email}")
    print(f"  🔐 Password: {password[:4]}****")
    print(f"  🌐 Proxy: {'Enabled' if use_proxy and CONFIG.get('proxy', {}).get('enabled') else 'None'}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        # Setup proxy from config
        proxy = get_proxy_config(CONFIG) if use_proxy else None
        if proxy:
            print(f"  🌐 Using Proxy: {CONFIG.get('proxy', {}).get('host')}:{CONFIG.get('proxy', {}).get('port')}")
        
        # Launch browser with stealth args
        browser = await p.chromium.launch(
            headless=False,  # Visible for debugging
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-gpu',
                '--lang=en-US',
            ]
        )
        
        # Context with realistic fingerprint
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles',
            permissions=['geolocation'],
            geolocation={'latitude': 33.3887, 'longitude': -111.8428},  # Mesa, AZ (ISP location)
        )
        
        # Apply stealth if available
        if has_stealth:
            stealth = Stealth()
            await stealth.apply_stealth_async(context)
            print("  🔒 Stealth mode applied")
        
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Step 0: Verify IP
            print("\n  [Step 0] Checking IP...")
            try:
                await page.goto("https://api.ipify.org?format=json", timeout=15000)
                await asyncio.sleep(1)
                ip_data = json.loads(await page.inner_text("body"))
                print(f"  ✓ IP: {ip_data.get('ip', 'Unknown')}")
            except Exception as e:
                print(f"  ⚠️ IP check failed: {e}")
            
            # Step 1: Go to ChatGPT homepage
            print("\n  [Step 1] Opening chatgpt.com...")
            await page.goto("https://chatgpt.com/", wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            
            # Check for Cloudflare challenge
            page_content = await page.content()
            if "Just a moment" in page_content or "cf-challenge" in page_content:
                print("  ⏳ Cloudflare challenge detected, waiting...")
                await asyncio.sleep(10)
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_1_home.png"))
            print(f"  📍 URL: {page.url}")
            
            # Step 2: Click Sign Up
            print("\n  [Step 2] Looking for Sign Up button...")
            
            # Wait for page to stabilize
            await asyncio.sleep(3)
            
            # Try to find and click sign up
            clicked = False
            selectors = [
                'text="Sign up"',
                'text="Sign up for free"',
                'button:has-text("Sign up")',
                'a:has-text("Sign up")',
                '[data-testid="login-button"]',  # Sometimes it's login that leads to signup
            ]
            
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        print(f"  ✓ Found: {sel}")
                        await loc.first.click()
                        clicked = True
                        await asyncio.sleep(5)
                        break
                except:
                    continue
            
            if not clicked:
                # Direct navigation to signup URL
                print("  📍 Button not found, navigating directly to signup URL...")
                await page.goto("https://chatgpt.com/auth/login?screen_hint=signup", wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)
            
            # Check for Cloudflare again
            page_content = await page.content()
            if "Just a moment" in page_content:
                print("  ⏳ Cloudflare challenge on auth page, waiting...")
                for i in range(12):
                    await asyncio.sleep(5)
                    page_content = await page.content()
                    if "Just a moment" not in page_content:
                        print("  ✓ Cloudflare passed!")
                        break
                    print(f"  ⏳ Still waiting... ({i+1}/12)")
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_2_signup.png"))
            print(f"  📍 URL: {page.url}")
            
            # Step 3: Enter email
            print("\n  [Step 3] Looking for email input...")
            
            email_found = False
            email_input = None
            
            for attempt in range(10):
                email_selectors = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[id*="email"]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="Email" i]',
                    '#email-input',
                ]
                
                for sel in email_selectors:
                    try:
                        loc = page.locator(sel)
                        if await loc.count() > 0 and await loc.first.is_visible():
                            email_input = loc.first
                            email_found = True
                            print(f"  ✓ Found email input: {sel}")
                            break
                    except:
                        continue
                
                if email_found:
                    break
                    
                print(f"  ⏳ Waiting for email field... ({attempt+1}/10)")
                await asyncio.sleep(3)
            
            if not email_found:
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_error_no_email.png"))
                result["error"] = "Email input not found"
                print("  ❌ Email input not found!")
                return result
            
            # Enter email with human-like typing
            await email_input.click()
            await asyncio.sleep(0.5)
            
            # Type slowly like human
            for char in email:
                await email_input.type(char, delay=random.randint(50, 150))
            
            print(f"  ✓ Email entered: {email}")
            await asyncio.sleep(1)
            
            # Click Continue (not OAuth buttons)
            continue_selectors = [
                'button:text-is("Continue")',
                'button[type="submit"]:has-text("Continue"):not(:has-text("with"))',
                'button:has-text("Continue"):not(:has-text("Google")):not(:has-text("Microsoft"))',
                'form button[type="submit"]',
            ]
            
            for sel in continue_selectors:
                try:
                    btn = page.locator(sel)
                    if await btn.count() > 0 and await btn.first.is_visible():
                        print(f"  ✓ Clicking: {sel}")
                        await btn.first.click()
                        await asyncio.sleep(5)
                        break
                except:
                    continue
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_3_after_email.png"))
            
            # Step 4: Enter password
            print("\n  [Step 4] Looking for password field...")
            
            password_found = False
            for attempt in range(10):
                try:
                    password_input = page.locator('input[type="password"]:visible')
                    if await password_input.count() > 0:
                        password_found = True
                        print("  ✓ Found password input")
                        break
                except:
                    pass
                    
                print(f"  ⏳ Waiting for password field... ({attempt+1}/10)")
                await asyncio.sleep(3)
            
            if password_found:
                await password_input.first.click()
                await asyncio.sleep(0.5)
                
                # Type password slowly
                for char in password:
                    await password_input.first.type(char, delay=random.randint(30, 100))
                
                print("  ✓ Password entered")
                await asyncio.sleep(1)
                
                # Click Continue
                for sel in ['button:text-is("Continue")', 'button[type="submit"]']:
                    try:
                        btn = page.locator(sel)
                        if await btn.count() > 0:
                            await btn.first.click()
                            await asyncio.sleep(5)
                            break
                    except:
                        continue
            else:
                print("  ⚠️ Password field not found")
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_4_after_pass.png"))
            
            # Step 5: Check verification or success
            print("\n  [Step 5] Checking result...")
            await asyncio.sleep(3)
            
            current_url = page.url.lower()
            try:
                page_text = (await page.inner_text('body')).lower()
            except:
                page_text = ""
            
            print(f"  📍 Final URL: {page.url}")
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_5_final.png"))
            
            # Check various outcomes
            if any(x in page_text for x in ["verify your email", "check your email", "verification", "sent you"]):
                print("  📬 Email verification required!")
                result["needs_verification"] = True
            elif "chat" in current_url and "auth" not in current_url:
                print("  🎉 Signup successful!")
                result["success"] = True
                
                # Try to get access token
                try:
                    token_data = await page.evaluate("""
                        () => {
                            try {
                                const nextData = document.getElementById('__NEXT_DATA__');
                                if (nextData) {
                                    const data = JSON.parse(nextData.textContent);
                                    return data.props?.pageProps?.accessToken || null;
                                }
                            } catch(e) {}
                            return null;
                        }
                    """)
                    if token_data:
                        result["access_token"] = token_data
                        print("  🔑 Access token retrieved!")
                except:
                    pass
                    
            elif "error" in current_url:
                result["error"] = "Auth error page"
            else:
                print("  ⚠️ Unknown state - check screenshots")
            
            # Keep browser open for inspection
            print(f"\n  ⏳ Browser stays open for 30s...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            result["error"] = str(e)
            try:
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_error.png"))
            except:
                pass
        finally:
            await browser.close()
    
    return result


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="ChatGPT Auth0 Signup with Stealth")
    parser.add_argument("--email", type=str, help="Email to use for signup")
    parser.add_argument("--password", type=str, help="Password to use")
    parser.add_argument("--no-proxy", action="store_true", help="Disable ISP proxy")
    args = parser.parse_args()
    
    # Generate email if not provided
    email = args.email
    if not email:
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"testuser_{random_str}@gmail.com"
        print(f"⚠️ Using test email: {email}")
        print("   For real signup, use: --email your@email.com")
    
    password = args.password or generate_password()
    use_proxy = not args.no_proxy
    
    result = await signup_with_stealth_isp(email, password, use_proxy)
    
    print("\n" + "="*60)
    print("  📊 RESULT")
    print("="*60)
    
    if result["success"]:
        print("  ✅ SUCCESS!")
        save_account(email, password, result.get("access_token"))
    elif result["needs_verification"]:
        print("  📬 Needs email verification")
        print(f"     Check inbox: {email}")
    else:
        print(f"  ❌ FAILED: {result.get('error', 'Unknown')}")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
