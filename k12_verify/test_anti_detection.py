"""
Anti-Detection Test Script

Tests the fingerprint spoofing system against popular detection sites:
- bot.sannysoft.com - General bot detection
- browserleaks.com/canvas - Canvas fingerprint
- browserleaks.com/webgl - WebGL fingerprint

Usage:
    python test_anti_detection.py
    python test_anti_detection.py --url https://bot.sannysoft.com
    python test_anti_detection.py --headless false
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
os.chdir(Path(__file__).parent)

import argparse
import time
import json
from datetime import datetime

# Import fingerprint system
from app.core.fingerprint_generator import FingerprintGenerator
from app.core.stealth_scripts import StealthScripts


def test_fingerprint_generation():
    """Test fingerprint generator."""
    print("=" * 60)
    print("TEST 1: Fingerprint Generation")
    print("=" * 60)
    
    # Generate Windows fingerprint
    fp = FingerprintGenerator.generate(os_type="windows", browser="chrome")
    
    print(f"\n  Profile ID: {fp.profile_id}")
    print(f"  Platform: {fp.platform}")
    print(f"  OS: {fp.os_name} {fp.os_version}")
    print(f"  Screen: {fp.screen_width}x{fp.screen_height}")
    print(f"  CPU Cores: {fp.hardware_concurrency}")
    print(f"  RAM: {fp.device_memory} GB")
    print(f"  WebGL Vendor: {fp.webgl_vendor}")
    print(f"  WebGL Renderer: {fp.webgl_renderer[:60]}...")
    print(f"  WebRTC Mode: {fp.webrtc_mode}")
    print(f"  Timezone: {fp.timezone} (offset: {fp.timezone_offset})")
    print(f"  Language: {fp.language}")
    print(f"  User-Agent: {fp.user_agent[:60]}...")
    
    print("\n  [OK] Fingerprint generated successfully!")
    return fp


def test_stealth_scripts(fp):
    """Test stealth script generation."""
    print("\n" + "=" * 60)
    print("TEST 2: Stealth Scripts Generation")
    print("=" * 60)
    
    js_code = StealthScripts.generate_all(fp)
    
    print(f"\n  JavaScript size: {len(js_code):,} characters")
    print(f"  Lines of code: {js_code.count(chr(10))}")
    
    # Check for key components
    components = {
        "navigator.webdriver": "webdriver" in js_code,
        "hardwareConcurrency": "hardwareConcurrency" in js_code,
        "WebGL vendor/renderer": "UNMASKED_VENDOR" in js_code,
        "Canvas toDataURL": "toDataURL" in js_code,
        "Audio fingerprint": "AudioBuffer" in js_code,
        "WebRTC protection": "RTCPeerConnection" in js_code,
        "Timezone override": "getTimezoneOffset" in js_code,
        "Screen dimensions": "screen" in js_code,
        "Media devices": "enumerateDevices" in js_code,
        "Client rects": "getBoundingClientRect" in js_code,
    }
    
    print("\n  Component checks:")
    all_ok = True
    for name, present in components.items():
        status = "[OK]" if present else "[MISSING]"
        if not present:
            all_ok = False
        print(f"    {status} {name}")
    
    if all_ok:
        print("\n  [OK] All stealth components present!")
    else:
        print("\n  [WARNING] Some components missing!")
    
    return js_code


def test_browser_detection(url: str = "https://bot.sannysoft.com", headless: bool = True):
    """Test browser against detection site."""
    print("\n" + "=" * 60)
    print(f"TEST 3: Browser Detection Test")
    print("=" * 60)
    print(f"  URL: {url}")
    print(f"  Headless: {headless}")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [ERROR] Playwright not installed")
        print("  Run: pip install playwright && playwright install chromium")
        return
    
    # Generate fingerprint
    fp = FingerprintGenerator.generate(os_type="windows", browser="chrome")
    js_code = StealthScripts.generate_all(fp)
    
    print(f"\n  Using fingerprint: {fp.profile_id}")
    print(f"  WebGL: {fp.webgl_renderer[:50]}...")
    
    # Screenshots dir
    screenshots_dir = Path("test_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        # Browser args
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-infobars',
            f'--window-size={fp.screen_width},{fp.screen_height}',
        ]
        
        if headless:
            browser_args.extend(['--disable-gpu', '--headless=new'])
        
        print("\n  Launching browser...")
        browser = p.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # Create context with fingerprint
        context = browser.new_context(
            viewport={"width": fp.screen_width, "height": fp.screen_avail_height},
            user_agent=fp.user_agent,
            locale=fp.language,
            timezone_id=fp.timezone,
            device_scale_factor=fp.device_pixel_ratio,
        )
        
        # Inject stealth scripts
        context.add_init_script(js_code)
        print("  Stealth scripts injected")
        
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # Navigate to detection site
        print(f"\n  Navigating to {url}...")
        page.goto(url, wait_until='networkidle')
        
        # Wait for page to fully load
        time.sleep(5)
        
        # Take screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"detection_test_{timestamp}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Screenshot saved: {screenshot_path}")
        
        # Try to extract test results (site-specific)
        if "sannysoft" in url:
            print("\n  Sannysoft Detection Results:")
            try:
                # Look for test results table
                results = page.evaluate("""
                    () => {
                        const results = {};
                        const rows = document.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const test = cells[0].textContent.trim();
                                const result = cells[1].textContent.trim();
                                if (test && result) {
                                    results[test] = result;
                                }
                            }
                        });
                        return results;
                    }
                """)
                
                for test, result in results.items():
                    status = "[OK]" if "missing" in result.lower() or "undefined" in result.lower() or result == "" else "[CHECK]"
                    if test.lower() in ["webdriver", "chrome", "permissions"]:
                        print(f"    {status} {test}: {result[:50]}")
            except Exception as e:
                print(f"    Could not parse results: {e}")
        
        elif "browserleaks" in url:
            print("\n  BrowserLeaks Results:")
            try:
                # Get page content
                content = page.content()
                if "canvas" in url:
                    print("    Canvas fingerprint test - check screenshot")
                elif "webgl" in url:
                    # Try to get WebGL info
                    webgl_info = page.evaluate("""
                        () => {
                            const canvas = document.createElement('canvas');
                            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                            if (!gl) return null;
                            const ext = gl.getExtension('WEBGL_debug_renderer_info');
                            if (!ext) return {vendor: 'N/A', renderer: 'N/A'};
                            return {
                                vendor: gl.getParameter(ext.UNMASKED_VENDOR_WEBGL),
                                renderer: gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)
                            };
                        }
                    """)
                    if webgl_info:
                        print(f"    WebGL Vendor: {webgl_info.get('vendor', 'N/A')}")
                        print(f"    WebGL Renderer: {webgl_info.get('renderer', 'N/A')[:60]}...")
            except Exception as e:
                print(f"    Could not parse results: {e}")
        
        # Check navigator properties
        print("\n  Navigator Properties (from browser):")
        nav_props = page.evaluate("""
            () => ({
                webdriver: navigator.webdriver,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                platform: navigator.platform,
                languages: navigator.languages,
            })
        """)
        
        for prop, value in nav_props.items():
            expected = ""
            if prop == "webdriver":
                expected = "(should be undefined)"
                status = "[OK]" if value is None or value == False else "[FAIL]"
            elif prop == "hardwareConcurrency":
                expected = f"(expected: {fp.hardware_concurrency})"
                status = "[OK]" if value == fp.hardware_concurrency else "[CHECK]"
            elif prop == "deviceMemory":
                expected = f"(expected: {fp.device_memory})"
                status = "[OK]" if value == fp.device_memory else "[CHECK]"
            elif prop == "platform":
                expected = f"(expected: {fp.platform})"
                status = "[OK]" if value == fp.platform else "[CHECK]"
            else:
                status = "[INFO]"
            
            print(f"    {status} {prop}: {value} {expected}")
        
        # Check WebGL
        print("\n  WebGL Properties (from browser):")
        webgl_props = page.evaluate("""
            () => {
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (!gl) return {error: 'No WebGL'};
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (!ext) return {error: 'No debug info extension'};
                    return {
                        vendor: gl.getParameter(ext.UNMASKED_VENDOR_WEBGL),
                        renderer: gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)
                    };
                } catch (e) {
                    return {error: e.toString()};
                }
            }
        """)
        
        if "error" in webgl_props:
            print(f"    [ERROR] {webgl_props['error']}")
        else:
            vendor_ok = webgl_props.get('vendor') == fp.webgl_vendor
            renderer_ok = webgl_props.get('renderer') == fp.webgl_renderer
            
            print(f"    {'[OK]' if vendor_ok else '[FAIL]'} Vendor: {webgl_props.get('vendor')}")
            print(f"    {'[OK]' if renderer_ok else '[FAIL]'} Renderer: {webgl_props.get('renderer', '')[:60]}...")
        
        # Keep browser open if not headless
        if not headless:
            print("\n  Browser open for inspection. Press Enter to close...")
            input()
        
        browser.close()
    
    print("\n  [OK] Browser detection test complete!")
    print(f"  Check screenshot: {screenshot_path}")


def main():
    parser = argparse.ArgumentParser(description="Test Anti-Detection System")
    parser.add_argument("--url", type=str, default="https://bot.sannysoft.com",
                       help="Detection test URL")
    parser.add_argument("--headless", type=str, default="true",
                       help="Run headless (true/false)")
    parser.add_argument("--skip-browser", action="store_true",
                       help="Skip browser test")
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("ANTI-DETECTION SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Fingerprint generation
    fp = test_fingerprint_generation()
    
    # Test 2: Stealth scripts
    js_code = test_stealth_scripts(fp)
    
    # Test 3: Browser detection
    if not args.skip_browser:
        headless = args.headless.lower() != "false"
        test_browser_detection(url=args.url, headless=headless)
    else:
        print("\n  [SKIP] Browser test skipped")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
