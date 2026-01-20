"""
Test Browser Verification with SheerID Link

Usage:
    python test_sheerid_browser.py "https://services.sheerid.com/verify/..."
    python test_sheerid_browser.py "https://services.sheerid.com/verify/..." --headless false
    python test_sheerid_browser.py "https://services.sheerid.com/verify/..." --email your@email.com
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
os.chdir(Path(__file__).parent)

import argparse
import asyncio
import os
from datetime import datetime


def status_callback(step: str, message: str):
    """Print status updates."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{step}] {message}")


async def main():
    parser = argparse.ArgumentParser(description="Test Browser Verification with SheerID")
    parser.add_argument("url", type=str, help="SheerID verification URL")
    parser.add_argument("--email", type=str, default=None, help="Custom email address")
    parser.add_argument("--headless", type=str, default="true", help="Run headless (true/false)")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy (direct connection)")
    args = parser.parse_args()
    
    # Validate URL
    if 'sheerid' not in args.url.lower():
        print("[ERROR] URL must be a SheerID verification link")
        print("Example: https://services.sheerid.com/verify/PROGRAM_ID/?verificationId=XXX")
        return
    
    print("=" * 70)
    print("SHEERID BROWSER VERIFICATION TEST")
    print("=" * 70)
    print(f"URL: {args.url[:60]}...")
    print(f"Email: {args.email or 'Auto-generated'}")
    print(f"Headless: {args.headless}")
    print("=" * 70)
    
    # Import verifier
    from app.core.browser_verifier import BrowserVerifier
    
    # Disable proxy if requested
    if getattr(args, 'no_proxy', False):
        print("[INFO] Proxy disabled - using direct connection")
        os.environ['PROXY_HOST'] = ''
        os.environ['PROXY_USER'] = ''
    
    # Create verifier
    headless = args.headless.lower() != "false"
    verifier = BrowserVerifier(
        sheerid_url=args.url,
        custom_email=args.email,
        status_callback=status_callback,
        headless=headless
    )
    
    print("\n[START] Starting browser verification...\n")
    
    # Run verification
    result = await verifier.verify()
    
    # Print result
    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    
    if result.get('success'):
        print("\n  *** VERIFICATION SUCCESSFUL! ***")
        if result.get('redirectUrl'):
            print(f"\n  Redirect URL:")
            print(f"  {result['redirectUrl']}")
    elif result.get('pending'):
        print("\n  Document submitted, pending review")
    elif result.get('rejected'):
        print("\n  REJECTED")
        print(f"  Reason: {result.get('message', 'Unknown')}")
    else:
        print("\n  FAILED")
        print(f"  Error: {result.get('message', 'Unknown error')}")
    
    # Print teacher info
    if result.get('teacher'):
        teacher = result['teacher']
        print(f"\n  Teacher: {teacher.get('first_name', '')} {teacher.get('last_name', '')}")
        print(f"  Email: {teacher.get('email', '')}")
    
    if result.get('fingerprint_id'):
        print(f"\n  Fingerprint: {result['fingerprint_id']}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
