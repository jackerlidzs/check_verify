"""Find exact selectors"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

NEW_URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=695828804ef52f78762eb4eb&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"

async def find_selectors():
    from playwright.async_api import async_playwright
    
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    
    await page.goto(NEW_URL, wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)
    
    # Get all inputs with details
    print("=== All inputs ===")
    inputs = page.locator('input')
    count = await inputs.count()
    for i in range(count):
        inp = inputs.nth(i)
        id_ = await inp.get_attribute('id') or ''
        name = await inp.get_attribute('name') or ''
        type_ = await inp.get_attribute('type') or 'text'
        placeholder = await inp.get_attribute('placeholder') or ''
        print(f"  [{i}] id='{id_}' name='{name}' type='{type_}' placeholder='{placeholder}'")
    
    # Get all buttons
    print("\n=== All buttons ===")
    buttons = page.locator('button')
    count = await buttons.count()
    for i in range(count):
        btn = buttons.nth(i)
        text = await btn.inner_text()
        type_ = await btn.get_attribute('type') or ''
        print(f"  [{i}] text='{text}' type='{type_}'")
    
    await browser.close()
    await p.stop()

if __name__ == "__main__":
    asyncio.run(find_selectors())
