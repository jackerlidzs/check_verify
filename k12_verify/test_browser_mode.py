"""
Test Browser Mode Improvements

Tests the enhanced browser_verifier.py features:
- SYNC Playwright API (no async/sync mixing)
- Human-like typing/clicking
- Fingerprint generation
- Geolocation matching

Usage:
    python test_browser_mode.py
    python test_browser_mode.py --headless false
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
os.chdir(Path(__file__).parent)

import argparse
import time

def test_imports():
    """Test all imports work correctly."""
    print("=" * 60)
    print("TEST 1: Imports")
    print("=" * 60)
    
    try:
        from app.core.browser_verifier import BrowserVerifier, TIMEZONE_GEOLOCATIONS
        from app.core.fingerprint_generator import FingerprintGenerator
        from app.core.stealth_scripts import StealthScripts
        print("  [OK] All imports successful")
        return True
    except Exception as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def test_fingerprint_geolocation():
    """Test fingerprint with geolocation matching."""
    print("\n" + "=" * 60)
    print("TEST 2: Fingerprint with Geolocation Matching")
    print("=" * 60)
    
    from app.core.browser_verifier import TIMEZONE_GEOLOCATIONS
    from app.core.fingerprint_generator import FingerprintGenerator
    
    # Generate fingerprint
    fp = FingerprintGenerator.generate(os_type="windows")
    
    print(f"\n  Fingerprint ID: {fp.profile_id}")
    print(f"  Timezone: {fp.timezone}")
    
    # Check geolocation matching
    if fp.timezone in TIMEZONE_GEOLOCATIONS:
        geo = TIMEZONE_GEOLOCATIONS[fp.timezone]
        print(f"  Geolocation: {geo['latitude']:.4f}, {geo['longitude']:.4f}")
        print("  [OK] Timezone has matching geolocation")
    else:
        print("  [WARN] Timezone not in geolocation map (will use default)")
    
    return True


def test_human_behavior():
    """Test human-like behavior methods."""
    print("\n" + "=" * 60)
    print("TEST 3: Human Behavior Methods")
    print("=" * 60)
    
    from app.core.browser_verifier import BrowserVerifier
    
    # Create verifier instance
    verifier = BrowserVerifier(
        sheerid_url="https://example.com",
        headless=True
    )
    
    # Check methods exist
    methods = [
        '_human_type',
        '_human_click',
        '_random_scroll',
        '_generate_document',
        '_take_error_screenshot',
    ]
    
    all_ok = True
    for method in methods:
        if hasattr(verifier, method):
            print(f"  [OK] {method}")
        else:
            print(f"  [FAIL] {method} missing")
            all_ok = False
    
    return all_ok


def test_browser_verification(headless: bool = True):
    """Test actual browser verification (requires Playwright)."""
    print("\n" + "=" * 60)
    print("TEST 4: Browser Verification (Quick)")
    print("=" * 60)
    print(f"  Headless: {headless}")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [SKIP] Playwright not installed")
        return True
    
    from app.core.browser_verifier import BrowserVerifier
    from app.core.fingerprint_generator import FingerprintGenerator
    from app.core.stealth_scripts import StealthScripts
    
    # Generate fingerprint
    fp = FingerprintGenerator.generate(os_type="windows")
    js_code = StealthScripts.generate_all(fp)
    
    print(f"\n  Profile: {fp.profile_id}")
    print(f"  WebGL: {fp.webgl_renderer[:50]}...")
    
    # Quick browser test
    print("\n  Launching browser...")
    
    with sync_playwright() as p:
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
        
        if headless:
            browser_args.extend(['--disable-gpu', '--headless=new'])
        
        browser = p.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        context = browser.new_context(
            viewport={"width": fp.screen_width, "height": fp.screen_avail_height},
            user_agent=fp.user_agent,
            locale=fp.language,
            timezone_id=fp.timezone,
        )
        
        # Inject stealth
        context.add_init_script(js_code)
        print("  Stealth scripts injected")
        
        page = context.new_page()
        
        # Test navigation
        print("  Navigating to bot.sannysoft.com...")
        page.goto("https://bot.sannysoft.com", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        # Check webdriver
        webdriver_value = page.evaluate("() => navigator.webdriver")
        webgl_vendor = page.evaluate("""
            () => {
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl');
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                } catch (e) { return 'N/A'; }
            }
        """)
        
        print(f"\n  navigator.webdriver: {webdriver_value}")
        print(f"  WebGL vendor: {webgl_vendor}")
        
        if webdriver_value is None or webdriver_value == False:
            print("  [OK] Webdriver hidden")
        else:
            print("  [FAIL] Webdriver detected!")
        
        if webgl_vendor == fp.webgl_vendor:
            print("  [OK] WebGL vendor spoofed correctly")
        else:
            print(f"  [CHECK] WebGL vendor: expected '{fp.webgl_vendor}'")
        
        browser.close()
    
    print("\n  [OK] Browser test completed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Test Browser Mode Improvements")
    parser.add_argument("--headless", type=str, default="true", help="Run headless (true/false)")
    parser.add_argument("--skip-browser", action="store_true", help="Skip browser test")
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("BROWSER MODE IMPROVEMENTS TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Fingerprint + Geolocation
    results.append(("Fingerprint/Geolocation", test_fingerprint_geolocation()))
    
    # Test 3: Human behavior methods
    results.append(("Human Behavior Methods", test_human_behavior()))
    
    # Test 4: Browser
    if not args.skip_browser:
        headless = args.headless.lower() != "false"
        results.append(("Browser Verification", test_browser_verification(headless)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  {status} {name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - check output above")
    print("=" * 60)


if __name__ == "__main__":
    main()
