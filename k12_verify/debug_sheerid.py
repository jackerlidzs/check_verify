"""
Debug SheerID page - take screenshot and capture HTML
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
import os
os.chdir(Path(__file__).parent)

from playwright.sync_api import sync_playwright

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    args = parser.parse_args()
    
    print(f"Opening: {args.url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Navigating...")
        page.goto(args.url, wait_until='networkidle', timeout=60000)
        
        print("Waiting 5 seconds...")
        page.wait_for_timeout(5000)
        
        # Screenshot
        screenshot_path = Path(__file__).parent / "debug_screenshot.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot: {screenshot_path}")
        
        # Check for form elements
        print("\nChecking form elements:")
        selectors = [
            '#sid-first-name',
            '#sid-last-name', 
            '#sid-email',
            'input[type="text"]',
            'input[type="email"]',
            '.sid-form',
            '.sheerid-container',
            'form',
        ]
        
        for sel in selectors:
            count = page.locator(sel).count()
            print(f"  {sel}: {count} found")
        
        # Page content
        print("\nPage title:", page.title())
        print("URL:", page.url)
        
        # Check for error messages
        error_els = page.locator('.error, .alert, [class*="error"], [class*="expired"]')
        if error_els.count() > 0:
            print("\nError messages found:")
            for i in range(min(3, error_els.count())):
                print(f"  - {error_els.nth(i).inner_text()[:100]}")
        
        print("\nKeeping browser open for 30 seconds...")
        page.wait_for_timeout(30000)
        
        browser.close()

if __name__ == "__main__":
    main()
