"""
Browser-based Military Verification
Uses Playwright to fill SheerID form, user clicks Submit manually
"""
import asyncio
import random
import logging
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, Browser

from .living_veteran_search import get_random_living_veteran

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import proxy manager
try:
    from config.proxy_manager import get_proxy_config
except ImportError:
    def get_proxy_config(): return None

# Month name mapping
MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# Branch name to display name mapping
BRANCH_DISPLAY = {
    "US ARMY": "Army",
    "US NAVY": "Navy", 
    "US AIR FORCE": "Air Force",
    "US MARINE CORPS": "Marine Corps",
    "US COAST GUARD": "Coast Guard",
    "US SPACE FORCE": "Space Force"
}


class BrowserVerifier:
    """Browser-based SheerID form filler using Playwright"""
    
    def __init__(self, verification_url: str, email: str = None):
        self.verification_url = verification_url
        self.email = email
        self.browser: Browser = None
        self.page: Page = None
    
    async def _human_delay(self, min_ms: int = 100, max_ms: int = 300):
        """Add human-like delay between actions"""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
    
    async def _type_slowly(self, selector: str, text: str):
        """Type text slowly like a human"""
        element = self.page.locator(selector)
        await element.click()
        await self._human_delay(50, 150)
        
        for char in text:
            await element.type(char, delay=random.uniform(50, 150))
        
        await self._human_delay(100, 200)
    
    async def fill_form(self, veteran_info: Dict) -> bool:
        """Fill the SheerID verification form"""
        try:
            async with async_playwright() as p:
                # Get proxy config
                proxy_config = get_proxy_config()
                
                browser_args = {
                    "headless": False,  # Show browser for user to see
                    "slow_mo": 100,     # Slow down actions
                }
                
                # Add proxy if configured
                if proxy_config and proxy_config.get("enabled"):
                    proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
                    browser_args["proxy"] = {"server": proxy_url}
                    logger.info(f"Using proxy: {proxy_config['host']}")
                
                # Launch browser
                logger.info("Launching browser...")
                self.browser = await p.chromium.launch(**browser_args)
                
                context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="en-US"
                )
                
                self.page = await context.new_page()
                
                # Navigate to verification URL
                logger.info(f"Navigating to: {self.verification_url}")
                await self.page.goto(self.verification_url, wait_until="networkidle")
                await self._human_delay(1000, 2000)
                
                # Step 1: Select Veteran status
                logger.info("Step 1: Selecting Veteran status...")
                try:
                    # Look for Veteran radio button or option
                    veteran_btn = self.page.locator("text=Veteran").first
                    await veteran_btn.click()
                    await self._human_delay(500, 1000)
                except Exception as e:
                    logger.warning(f"Could not find Veteran button: {e}")
                
                # Wait for form to load
                await self._human_delay(1000, 2000)
                
                # Step 2: Fill personal info
                logger.info("Step 2: Filling personal info...")
                
                # First Name
                first_name = veteran_info["first_name"]
                logger.info(f"  First Name: {first_name}")
                try:
                    await self._type_slowly('input[name="firstName"]', first_name)
                except:
                    await self._type_slowly('input[placeholder*="First"]', first_name)
                
                await self._human_delay(200, 400)
                
                # Last Name
                last_name = veteran_info["last_name"]
                logger.info(f"  Last Name: {last_name}")
                try:
                    await self._type_slowly('input[name="lastName"]', last_name)
                except:
                    await self._type_slowly('input[placeholder*="Last"]', last_name)
                
                await self._human_delay(200, 400)
                
                # Birth Date
                birth_date = veteran_info["birth_date"]  # YYYY-MM-DD
                year, month, day = birth_date.split("-")
                month_name = MONTHS[int(month)]
                
                logger.info(f"  Birth Date: {month_name} {day}, {year}")
                
                # Select birth month
                try:
                    month_select = self.page.locator('select[name*="birthMonth"], select[aria-label*="Month"]').first
                    await month_select.select_option(label=month_name)
                except Exception as e:
                    logger.warning(f"Could not select month: {e}")
                
                await self._human_delay(200, 400)
                
                # Fill birth day
                try:
                    day_input = self.page.locator('input[name*="birthDay"], input[placeholder*="Day"]').first
                    await day_input.fill(day.lstrip("0"))
                except Exception as e:
                    logger.warning(f"Could not fill day: {e}")
                
                await self._human_delay(200, 400)
                
                # Fill birth year
                try:
                    year_input = self.page.locator('input[name*="birthYear"], input[placeholder*="Year"]').first
                    await year_input.fill(year)
                except Exception as e:
                    logger.warning(f"Could not fill year: {e}")
                
                await self._human_delay(300, 600)
                
                # Branch of Service
                branch = veteran_info.get("branch", "US ARMY")
                branch_display = BRANCH_DISPLAY.get(branch, "Army")
                logger.info(f"  Branch: {branch_display}")
                
                try:
                    branch_select = self.page.locator('select[name*="organization"], div[class*="org"]').first
                    await branch_select.click()
                    await self._human_delay(300, 500)
                    
                    # Type to search
                    await self.page.keyboard.type(branch_display)
                    await self._human_delay(500, 800)
                    await self.page.keyboard.press("Enter")
                except Exception as e:
                    logger.warning(f"Could not select branch: {e}")
                
                await self._human_delay(300, 600)
                
                # Discharge Date
                discharge_date = veteran_info["discharge_date"]  # YYYY-MM-DD
                d_year, d_month, d_day = discharge_date.split("-")
                d_month_name = MONTHS[int(d_month)]
                
                logger.info(f"  Discharge Date: {d_month_name} {d_day}, {d_year}")
                
                # Select discharge month
                try:
                    d_month_select = self.page.locator('select[name*="dischargeMonth"]').first
                    await d_month_select.select_option(label=d_month_name)
                except Exception as e:
                    logger.warning(f"Could not select discharge month: {e}")
                
                await self._human_delay(200, 400)
                
                # Fill discharge day
                try:
                    d_day_input = self.page.locator('input[name*="dischargeDay"]').first
                    await d_day_input.fill(d_day.lstrip("0"))
                except Exception as e:
                    logger.warning(f"Could not fill discharge day: {e}")
                
                await self._human_delay(200, 400)
                
                # Fill discharge year
                try:
                    d_year_input = self.page.locator('input[name*="dischargeYear"]').first
                    await d_year_input.fill(d_year)
                except Exception as e:
                    logger.warning(f"Could not fill discharge year: {e}")
                
                await self._human_delay(300, 600)
                
                # Email
                email = self.email or f"vet{random.randint(10000, 99999)}@gmail.com"
                logger.info(f"  Email: {email}")
                
                try:
                    await self._type_slowly('input[name="email"], input[type="email"]', email)
                except Exception as e:
                    logger.warning(f"Could not fill email: {e}")
                
                # Done filling - notify user
                logger.info("")
                logger.info("=" * 60)
                logger.info("FORM FILLED - WAITING FOR USER")
                logger.info("=" * 60)
                logger.info("")
                logger.info("Please review the form and click SUBMIT manually.")
                logger.info("Press Enter in this terminal when done...")
                logger.info("")
                
                # Wait for user input
                input("Press Enter after you've submitted the form...")
                
                # Take screenshot
                await self.page.screenshot(path="verification_result.png")
                logger.info("Screenshot saved: verification_result.png")
                
                return True
                
        except Exception as e:
            logger.error(f"Browser verification failed: {e}")
            return False
        
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    """CLI for browser-based verification"""
    import sys
    
    print("=" * 60)
    print("BROWSER-BASED MILITARY VERIFICATION")
    print("=" * 60)
    print()
    
    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter SheerID verification URL: ").strip()
    
    if not url:
        print("[ERROR] No URL provided")
        return 1
    
    # Get email
    email = input("Enter your email (or press Enter for random): ").strip()
    if not email:
        email = None
    
    # Get veteran info
    veteran = get_random_living_veteran()
    
    print()
    print("Using veteran info:")
    print(f"  Name: {veteran['first_name']} {veteran['last_name']}")
    print(f"  Birth: {veteran['birth_date']}")
    print(f"  Branch: {veteran['branch']}")
    print(f"  Discharge: {veteran['discharge_date']}")
    print()
    
    # Run verification
    verifier = BrowserVerifier(url, email)
    success = await verifier.fill_form(veteran)
    
    print()
    print("=" * 60)
    print("RESULT:", "SUCCESS" if success else "FAILED")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    asyncio.run(main())
