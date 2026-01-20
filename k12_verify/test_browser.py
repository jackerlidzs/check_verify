"""Test Full Verification Flow with BrowserVerifier"""
import asyncio
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=69596525dc2d116d71e6ac33&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

async def test_full_flow():
    log("=== Full Verification Flow Test ===")
    log(f"URL: {URL[:60]}...")
    
    log("\n[1] Importing BrowserVerifier...")
    try:
        from app.core.browser_verifier import BrowserVerifier
        log("    ✅ Import OK")
    except Exception as e:
        log(f"    ❌ Import failed: {e}")
        return
    
    log("\n[2] Creating BrowserVerifier...")
    def callback(step, msg):
        log(f"    [{step}] {msg}")
    
    verifier = BrowserVerifier(
        sheerid_url=URL,
        custom_email="test@test.com",
        status_callback=callback,
        headless=True
    )
    log("    ✅ Instance created")
    
    log("\n[3] Running verify() with 120s timeout...")
    try:
        result = await asyncio.wait_for(verifier.verify(), timeout=120)
        
        log("\n" + "="*50)
        log("RESULT")
        log("="*50)
        log(f"Success: {result.get('success')}")
        log(f"URL: {result.get('redirectUrl', 'N/A')[:60]}")
        log(f"Message: {result.get('message', 'N/A')}")
        
        if result.get('success'):
            log("\n🎉 VERIFICATION SUCCESSFUL!")
        elif result.get('pending'):
            log("\n⏳ PENDING - needs doc upload or review")
        else:
            log("\n❌ FAILED")
            
    except asyncio.TimeoutError:
        log("\n❌ TIMEOUT after 120 seconds!")
    except Exception as e:
        log(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    log("\n=== DONE ===")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
