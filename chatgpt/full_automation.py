"""
ChatGPT Full Automation Signup
- Supports multiple email providers (Telegram bot or 22.do API)
- Playwright Stealth
- ISP Proxy support
- Auto receive verification code
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import random

# Import shared utilities
from utils import (
    load_config,
    generate_password,
    save_account,
    get_proxy_config,
    SCREENSHOTS_DIR,
)

# Import email providers
from email_providers import get_email_provider

# Load config on import
CONFIG = load_config()


async def signup_full_automation(use_proxy: bool = True, num_accounts: int = 1):
    """
    Full automation: Email provider + Stealth signup + Verification
    Supports both Telegram bot and 22.do API based on config.
    """
    from playwright.async_api import async_playwright
    
    try:
        from playwright_stealth import Stealth
        has_stealth = True
    except ImportError:
        print("  ⚠️ playwright-stealth not installed")
        has_stealth = False
    
    provider_type = CONFIG.get("email_provider", {}).get("type", "telegram")
    
    print("\n" + "="*60)
    print("  🚀 ChatGPT Full Automation Signup")
    print("="*60)
    print(f"  Email Provider: {provider_type}")
    print(f"  Accounts to create: {num_accounts}")
    print(f"  Proxy: {'ISP' if use_proxy else 'None'}")
    print("="*60 + "\n")
    
    # Get email provider based on config
    try:
        email_provider = get_email_provider(CONFIG)
    except ValueError as e:
        print(f"  ❌ Email provider error: {e}")
        return
    
    try:
        await email_provider.connect()
    except Exception as e:
        print(f"  ❌ Email provider connection failed: {e}")
        return
    
    # Cleanup existing emails if using Telegram
    if hasattr(email_provider, 'get_email_list'):
        try:
            current_emails = await email_provider.get_email_list()
            print(f"  📧 Current emails: {len(current_emails)}")
            if len(current_emails) >= 4:
                await email_provider.cleanup_all_emails()
        except:
            pass  # Not all providers support listing
    
    created = 0
    
    for i in range(num_accounts):
        print(f"\n{'='*60}")
        print(f"  📝 Account {i+1}/{num_accounts}")
        print("="*60)
        
        # Get temp email
        email = await email_provider.get_new_email()
        if not email:
            print("  ❌ Could not get email, skipping")
            continue
        
        password = generate_password()
        print(f"  📧 Email: {email}")
        print(f"  🔐 Password: {password}")
        
        # Signup with browser (pass email_provider for verification code handling)
        result = await browser_signup(email, password, use_proxy, has_stealth, email_provider)
        
        if result.get("needs_verification"):
            print("\n  📬 Waiting for email verification...")
            verification = await email_provider.wait_for_verification(timeout=180)
            
            if verification:
                if verification["type"] == "link":
                    # Click verification link
                    print("  🔗 Opening verification link...")
                    result = await complete_verification_link(verification["value"], use_proxy, has_stealth)
                elif verification["type"] == "code":
                    # Enter code (would need to implement)
                    print(f"  🔢 Code: {verification['value']}")
                    print("  ⚠️ Manual code entry may be needed")
        
        if result.get("success"):
            save_account(email, password, result.get("access_token"))
            created += 1
            print(f"  🎉 Account created successfully!")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown')}")
        
        # Cleanup email
        await email_provider.delete_email(email)
        
        # Delay between accounts
        if i < num_accounts - 1:
            delay = random.randint(20, 40)
            print(f"\n  ⏳ Waiting {delay}s before next account...")
            await asyncio.sleep(delay)
    
    await email_provider.disconnect()
    
    print(f"\n{'='*60}")
    print(f"  📊 SUMMARY")
    print("="*60)
    print(f"  ✅ Created: {created}/{num_accounts}")
    print("="*60)


async def browser_signup(email: str, password: str, use_proxy: bool, has_stealth: bool, email_provider=None):
    """Browser signup flow with email verification code support.
    
    Flow: Email → Get Code → Enter Code → Password → Submit
    """
    from playwright.async_api import async_playwright
    
    result = {"success": False, "needs_verification": False, "access_token": None, "error": None}
    safe_email = email.split('@')[0][:15]
    
    # Hazetunnel for TLS fingerprint bypass
    hazetunnel_proxy = None
    try:
        from hazetunnel import HazeTunnel
        HAS_HAZETUNNEL = True
    except ImportError:
        HAS_HAZETUNNEL = False
    
    headless = CONFIG.get("signup", {}).get("headless", False)
    use_hazetunnel = CONFIG.get("signup", {}).get("use_hazetunnel", False)
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    
    async with async_playwright() as p:
        proxy = get_proxy_config(CONFIG) if use_proxy else None
        
        # Setup Hazetunnel if enabled (for TLS fingerprint bypass)
        if use_hazetunnel and HAS_HAZETUNNEL:
            try:
                upstream = None
                if proxy:
                    upstream = f"http://{proxy['username']}:{proxy['password']}@{proxy['server']}"
                
                hazetunnel_proxy = HazeTunnel(
                    user_agent=user_agent,
                    upstream_proxy=upstream
                )
                hazetunnel_proxy.launch()
                proxy = {"server": hazetunnel_proxy.url}
                print(f"  🔮 Hazetunnel TLS bypass: {hazetunnel_proxy.url}")
            except Exception as e:
                print(f"  ⚠️ Hazetunnel failed: {e}, using direct connection")
                hazetunnel_proxy = None
        
        browser = await p.chromium.launch(
            headless=headless,
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--ignore-certificate-errors',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/Los_Angeles',
            ignore_https_errors=True,
        )
        
        # Apply stealth if available
        if has_stealth:
            from playwright_stealth import Stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(context)
        
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Step 1: Go to ChatGPT signup
            print("  🌐 Opening ChatGPT...")
            await page.goto("https://chatgpt.com/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)
            
            # Click Sign Up
            try:
                signup_btn = page.locator('text="Sign up for free"')
                if await signup_btn.count() > 0:
                    await signup_btn.first.click()
                    await asyncio.sleep(2)
            except:
                await page.goto("https://chatgpt.com/auth/login?screen_hint=signup", timeout=60000)
                await asyncio.sleep(2)
            
            # Wait for Cloudflare if needed
            for _ in range(10):
                content = await page.content()
                if "Just a moment" not in content:
                    break
                await asyncio.sleep(3)
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_1_home.png"))
            
            # Step 2: Enter email
            print("  📧 Entering email...")
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state="visible", timeout=30000)
            
            await email_input.fill(email)  # Fast fill instead of char-by-char
            await asyncio.sleep(0.5)
            
            # Click Continue
            continue_btn = page.locator('button:has-text("Continue"):not(:has-text("with"))')
            if await continue_btn.count() > 0:
                await continue_btn.first.click()
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_2_after_email.png"))
            print(f"  📍 URL: {page.url}")
            
            # Step 3: Check if we're on password page or need verification code
            current_url = page.url.lower()
            page_text = ""
            try:
                page_text = (await page.inner_text('body')).lower()
            except:
                pass
            
            # Check if password field is visible (new account flow)
            password_input = page.locator('input[type="password"]:visible')
            has_password_field = await password_input.count() > 0
            
            # Check if we're on a verification code page (NOT password page)
            code_input = page.locator('input[inputmode="numeric"], input[maxlength="1"]')
            is_code_page = await code_input.count() > 0 and not has_password_field
            
            if is_code_page and email_provider:
                # Email entered → Code needed before password
                print("  📬 Verification code required, waiting for email...")
                
                # Wait for verification code from email
                verification = await email_provider.wait_for_verification(timeout=120)
                
                if verification and verification.get("type") == "code":
                    code = verification["value"]
                    print(f"  🔢 Got code: {code}")
                    
                    # Find and enter the code
                    await asyncio.sleep(2)
                    
                    # Check if there are multiple single-digit inputs
                    single_inputs = page.locator('input[maxlength="1"]')
                    if await single_inputs.count() >= 6:
                        # Enter code digit by digit
                        print("  🔢 Entering code digit by digit...")
                        for i, digit in enumerate(code[:6]):
                            try:
                                input_field = single_inputs.nth(i)
                                await input_field.fill(digit)
                                await asyncio.sleep(0.2)
                            except:
                                pass
                    else:
                        # Single input for full code
                        code_inputs = page.locator('input[inputmode="numeric"], input[type="text"]:visible')
                        if await code_inputs.count() > 0:
                            code_field = code_inputs.first
                            await code_field.click()
                            await code_field.fill(code)
                    
                    await asyncio.sleep(2)
                    
                    # Try to click verify/continue button
                    verify_btn = page.locator('button:has-text("Continue"), button:has-text("Verify"), button[type="submit"]')
                    if await verify_btn.count() > 0:
                        await verify_btn.first.click()
                        await asyncio.sleep(2)
                    
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_3_after_code.png"))
                    print(f"  📍 URL after code: {page.url}")
                else:
                    print("  ⚠️ No verification code received")
                    result["needs_verification"] = True
                    return result
            
            # Step 4: Wait for and enter password
            print("  🔍 Looking for password field...")
            
            # Wait explicitly for password field to appear
            password_input = page.locator('input[type="password"]')
            try:
                await password_input.wait_for(state="attached", timeout=10000)
                print("  ✅ Password field found!")
                
                await asyncio.sleep(1)  # Let page fully render
                await password_input.click()
                await asyncio.sleep(0.5)
                
                # Type password character by character
                for char in password:
                    await password_input.type(char, delay=random.randint(30, 100))
                await asyncio.sleep(1)
                
                print(f"  ✅ Password entered: {'*' * len(password)}")
                
                # Submit
                submit_btn = page.locator('button[type="submit"], button:has-text("Continue")')
                if await submit_btn.count() > 0:
                    await submit_btn.first.click()
                    print("  ✅ Password submitted")
                await asyncio.sleep(2)
                
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_4_after_password.png"))
            except Exception as e:
                print(f"  ⚠️ Password field error: {e}")
                # Take screenshot for debugging
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_4_no_password.png"))
            
            # Step 5: Check for email verification after password
            await asyncio.sleep(1)
            current_url = page.url.lower()
            try:
                page_text = (await page.inner_text('body')).lower()
            except:
                page_text = ""
            
            print(f"  📍 URL after password: {page.url}")
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_5_check.png"))
            
            # Check if email verification is needed (new ChatGPT flow)
            if "email-verification" in current_url or "verify" in page_text:
                print("  📬 Email verification required after password...")
                
                if email_provider:
                    # Wait for verification code
                    verification = await email_provider.wait_for_verification(timeout=120)
                    
                    if verification and verification.get("type") == "code":
                        code = verification["value"]
                        print(f"  🔢 Got verification code: {code}")
                        
                        await asyncio.sleep(2)
                        
                        # Find code input fields
                        single_inputs = page.locator('input[maxlength="1"]')
                        code_inputs = page.locator('input[inputmode="numeric"], input[name*="code"], input[type="text"]:visible')
                        
                        if await single_inputs.count() >= 6:
                            # Enter code digit by digit
                            print("  🔢 Entering code digit by digit...")
                            for i, digit in enumerate(code[:6]):
                                try:
                                    input_field = single_inputs.nth(i)
                                    await input_field.fill(digit)
                                    await asyncio.sleep(0.2)
                                except:
                                    pass
                        elif await code_inputs.count() > 0:
                            # Single input for full code
                            code_field = code_inputs.first
                            await code_field.click()
                            await code_field.fill(code)
                        
                        await asyncio.sleep(3)
                        
                        # Click verify/continue button if needed
                        verify_btn = page.locator('button:has-text("Continue"), button:has-text("Verify"), button[type="submit"]')
                        if await verify_btn.count() > 0:
                            await verify_btn.first.click()
                            await asyncio.sleep(5)
                        
                        await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_6_after_code.png"))
                        print(f"  📍 URL after code: {page.url}")
                        
                        # Re-check final URL
                        current_url = page.url.lower()
                    else:
                        print("  ⚠️ No verification code received")
                        result["needs_verification"] = True
                else:
                    result["needs_verification"] = True
            
            # Step 6: Handle "About You" page (name + birthday)
            await asyncio.sleep(2)
            current_url = page.url.lower()
            
            if "about-you" in current_url or "about_you" in current_url:
                print("  👤 Filling 'About You' form...")
                
                try:
                    # Generate random name
                    first_names = ["John", "Jane", "Alex", "Sam", "Chris", "Taylor", "Jordan", "Morgan"]
                    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson"]
                    first_name = random.choice(first_names)
                    last_name = random.choice(last_names)
                    
                    # Fill name field (usually single input or two inputs)
                    name_inputs = page.locator('input[name*="name" i], input[placeholder*="name" i], input[type="text"]:visible')
                    if await name_inputs.count() >= 2:
                        # First and last name separately
                        await name_inputs.nth(0).fill(first_name)
                        await asyncio.sleep(0.5)
                        await name_inputs.nth(1).fill(last_name)
                    elif await name_inputs.count() == 1:
                        await name_inputs.first.fill(f"{first_name} {last_name}")
                    
                    await asyncio.sleep(1)
                    
                    # Handle birthday - generate random (18-25 years old)
                    birth_year = random.randint(2001, 2008)
                    birth_month = random.randint(1, 12)
                    birth_day = random.randint(1, 28)
                    
                    # Try different birthday input formats
                    birthday_str = f"{birth_month:02d}/{birth_day:02d}/{birth_year}"
                    birthday_filled = False
                    
                    # Method 1: Tab from name field to birthday field
                    try:
                        await page.keyboard.press("Tab")
                        await asyncio.sleep(0.5)
                        await page.keyboard.type(birthday_str, delay=50)
                        print(f"  📅 Birthday (Tab+type): {birthday_str}")
                        birthday_filled = True
                    except Exception as e:
                        print(f"  ⚠️ Tab method failed: {e}")
                    
                    # Method 2: Click directly on the input field area  
                    if not birthday_filled:
                        try:
                            # Try clicking below the name input (birthday input is below)
                            name_input = page.locator('input:visible').first
                            if await name_input.count() > 0:
                                box = await name_input.bounding_box()
                                if box:
                                    # Click below the name input
                                    await page.mouse.click(box['x'] + 100, box['y'] + 80)
                                    await asyncio.sleep(0.5)
                                    await page.keyboard.type(birthday_str, delay=50)
                                    print(f"  📅 Birthday (mouse): {birthday_str}")
                                    birthday_filled = True
                        except:
                            pass
                    
                    if not birthday_filled:
                        print("  ⚠️ Could not find birthday input")
                    
                    await asyncio.sleep(1)
                    
                    # Submit
                    submit_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Agree")')
                    if await submit_btn.count() > 0:
                        await submit_btn.first.click()
                        print("  ✅ About You form submitted")
                    
                    await asyncio.sleep(2)
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_8_after_about.png"))
                    
                except Exception as e:
                    print(f"  ⚠️ About You form error: {e}")
            
            # Step 7: Final result check
            await asyncio.sleep(2)
            current_url = page.url.lower()
            try:
                page_text = (await page.inner_text('body')).lower()
            except:
                page_text = ""
            
            print(f"  📍 Final URL: {page.url}")
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_9_final.png"))
            
            if "chat" in current_url and "auth" not in current_url:
                result["success"] = True
                print("  🎉 Signup successful!")
            elif any(x in page_text for x in ["verify your email", "check your email"]):
                result["needs_verification"] = True
            else:
                # Check for any error messages
                if "already" in page_text or "exists" in page_text:
                    result["error"] = "Email already exists"
                elif "invalid" in page_text:
                    result["error"] = "Invalid email or password"
            
            await asyncio.sleep(3)
            
        except Exception as e:
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            try:
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_email}_error.png"))
            except:
                pass
        finally:
            await browser.close()
            # Cleanup Hazetunnel
            if hazetunnel_proxy:
                try:
                    hazetunnel_proxy.stop()
                except:
                    pass
    
    return result


async def complete_verification_link(link: str, use_proxy: bool, has_stealth: bool):
    """Open verification link to complete signup."""
    from playwright.async_api import async_playwright
    
    result = {"success": False}
    
    async with async_playwright() as p:
        proxy = get_proxy_config(CONFIG) if use_proxy else None
        
        browser = await p.chromium.launch(headless=False, proxy=proxy)
        context = await browser.new_context()
        
        if has_stealth:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(context)
        
        page = await context.new_page()
        
        try:
            await page.goto(link, timeout=60000)
            await asyncio.sleep(10)
            
            # Check if successful
            current_url = page.url.lower()
            if "chat" in current_url and "auth" not in current_url:
                result["success"] = True
                print("  ✅ Email verified!")
                
                # Try to get token
                try:
                    token = await page.evaluate("""
                        () => {
                            const el = document.getElementById('__NEXT_DATA__');
                            if (el) {
                                return JSON.parse(el.textContent).props?.pageProps?.accessToken;
                            }
                        }
                    """)
                    if token:
                        result["access_token"] = token
                except:
                    pass
            
            await asyncio.sleep(5)
            
        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()
    
    return result


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=1, help="Number of accounts")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup all temp emails")
    args = parser.parse_args()
    
    if args.cleanup:
        try:
            email_provider = get_email_provider(CONFIG)
            await email_provider.connect()
            await email_provider.cleanup_all_emails()
            await email_provider.disconnect()
            print("✅ Cleanup complete")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    else:
        await signup_full_automation(
            use_proxy=not args.no_proxy,
            num_accounts=args.num
        )


if __name__ == "__main__":
    asyncio.run(main())
