"""
Live verification run - directly uses browser_verifier_sync.
Saves screenshots and logs for debugging.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).parent)

# Import app modules
from app.core.browser_verifier_sync import run_sync_verification

# Fresh SheerID URL - UPDATE THIS
SHEERID_URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=695ab78c83811641c662ce6f&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"

def log_callback(step: str, message: str = ""):
    """Log callback for verification."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if message:
        print(f"[{timestamp}] {step}: {message}")
    else:
        print(f"[{timestamp}] {step}")

def main():
    print("="*60)
    print("🚀 LIVE VERIFICATION RUN - NYC DOE PRIORITY")
    print("="*60)
    
    # Use NYC DOE teacher for highest instant verification chance
    from app.core.name_generator import get_high_priority_teacher
    
    teacher = get_high_priority_teacher()
    if not teacher:
        print("❌ No teachers found!")
        return None
    
    # Use teacher's school from their profile
    school = {
        'name': teacher.get('school_name', 'Bronx High School of Science'),
        'id': teacher.get('school_id', 'nyc_doe_1')
    }
    
    print(f"\n📋 Teacher: {teacher['first_name']} {teacher['last_name']}")
    print(f"📧 Email: {teacher['email']}")
    print(f"🏫 School: {school['name']}")
    print(f"🎯 District: NYC DOE (high instant-verify rate)")
    print(f"🔗 URL: {SHEERID_URL[:60]}...")
    print("="*60)
    
    # Proxy config (optional)
    proxy_config = None  # Set if needed
    
    print("\n🌐 Starting browser verification...")
    print("-"*60)
    
    # Run verification (browser stays open)
    result = run_sync_verification(
        sheerid_url=SHEERID_URL,
        teacher_data=teacher,
        school=school,
        proxy_config=proxy_config,
        status_callback=log_callback,
        headless=False,  # Show browser
        keep_open=True   # Keep browser open for user to see
    )
    
    print("-"*60)
    print("\n📊 RESULT:")
    print("="*60)
    
    if result.get('success'):
        print("🎉 VERIFICATION SUCCESSFUL!")
        print(f"   Redirect URL: {result.get('redirectUrl', 'N/A')}")
    elif result.get('email_sent'):
        print("📧 EMAIL VERIFICATION SENT")
        print(f"   Check inbox: {teacher['email']}")
        print(f"   Message: {result.get('message', 'Check email')}")
    elif result.get('pending'):
        print("⏳ VERIFICATION PENDING")
        print(f"   Message: {result.get('message', 'Check email')}")
    elif result.get('rejected'):
        print("❌ VERIFICATION REJECTED")
        print(f"   Error: {result.get('message', 'Unknown')}")
    else:
        print("⚠️ UNKNOWN STATUS")
        print(f"   Result: {result}")
    
    print("="*60)
    return result

if __name__ == "__main__":
    try:
        result = main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
