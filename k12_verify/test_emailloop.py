"""
Test script for Mail.tm emailLoop verification.
Tests the complete email verification flow:
1. Create temporary email via Mail.tm
2. Submit email to SheerID 
3. Wait for verification email
4. Extract and submit token
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
os.chdir(Path(__file__).parent)

import time
import httpx
import re
from app.core.mailtm_client import MailTmClient

# Constants
SHEERID_BASE_URL = "https://services.sheerid.com"

def status_callback(step, message):
    """Print status updates."""
    print(f"[{step}] {message}")

def test_mail_tm_basic():
    """Test basic Mail.tm functionality."""
    print("=" * 60)
    print("TEST 1: Mail.tm Basic Functionality")
    print("=" * 60)
    
    client = MailTmClient(status_callback=status_callback)
    
    # Get domains
    print("\n1. Getting domains...")
    domains = client.get_domains()
    print(f"   Available domains: {domains}")
    
    if not domains:
        print("   ❌ FAILED: No domains available")
        return None
    print(f"   ✅ Found {len(domains)} domain(s)")
    
    # Create account
    print("\n2. Creating email account...")
    email, password = client.create_account()
    
    if not email:
        print("   ❌ FAILED: Could not create account")
        return None
    print(f"   ✅ Email: {email}")
    print(f"   ✅ Token: {client.token[:20]}..." if client.token else "   ⚠️ No token")
    
    # Check inbox
    print("\n3. Checking inbox...")
    messages = client.get_messages()
    print(f"   ✅ Inbox: {len(messages)} messages")
    
    print("\n   ✅ Mail.tm is working!")
    return client

def test_sheerid_email_endpoints():
    """Test SheerID email-related API endpoints."""
    print("\n" + "=" * 60)
    print("TEST 2: SheerID Email API Endpoints")
    print("=" * 60)
    
    print("\nThis test requires a verification ID in emailLoop state.")
    print("You can get this by running a verification until it reaches emailLoop step.")
    
    verification_id = input("\nEnter verification ID (or press Enter to skip): ").strip()
    
    if not verification_id:
        print("   Skipped.")
        return
    
    http_client = httpx.Client(
        timeout=30.0,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    )
    
    try:
        # Check current status
        print(f"\n1. Checking verification status...")
        resp = http_client.get(
            f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}"
        )
        
        if resp.status_code == 200:
            data = resp.json()
            current_step = data.get('currentStep', 'unknown')
            print(f"   Current step: {current_step}")
            
            if current_step != 'emailLoop':
                print(f"   ⚠️ Not in emailLoop state (current: {current_step})")
                return
        else:
            print(f"   ❌ Failed: {resp.status_code} - {resp.text[:200]}")
            return
        
        # Create temp email
        print("\n2. Creating temporary email...")
        mail_client = MailTmClient(status_callback=status_callback)
        email, _ = mail_client.create_account()
        
        if not email:
            print("   ❌ Failed to create email")
            return
        print(f"   ✅ Email: {email}")
        
        # Try different submission methods
        print("\n3. Testing email submission to SheerID...")
        
        endpoints = [
            # Method 1: POST to emailLoop step with email
            {
                'name': 'POST /step/emailLoop (email)',
                'url': f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/step/emailLoop",
                'body': {'email': email}
            },
            # Method 2: POST resendEmail
            {
                'name': 'POST /resendEmail',
                'url': f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/resendEmail",
                'body': {'email': email}
            },
            # Method 3: POST updateEmail
            {
                'name': 'POST /updateEmail',
                'url': f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/updateEmail",
                'body': {'email': email}
            },
        ]
        
        successful_endpoint = None
        
        for endpoint in endpoints:
            print(f"\n   Trying: {endpoint['name']}...")
            try:
                resp = http_client.post(endpoint['url'], json=endpoint['body'])
                print(f"   Status: {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                
                if resp.status_code in [200, 201]:
                    successful_endpoint = endpoint['name']
                    print(f"   ✅ SUCCESS!")
                    break
            except Exception as e:
                print(f"   Error: {e}")
        
        if not successful_endpoint:
            print("\n   ❌ All endpoints failed")
            mail_client.close()
            return
        
        # Wait for email
        print(f"\n4. Waiting for SheerID verification email (2 min max)...")
        token = mail_client.wait_for_sheerid_email(
            verification_id=verification_id,
            max_wait=120,
            poll_interval=5
        )
        
        if token:
            print(f"   ✅ Got token: {token}")
            
            # Submit token
            print("\n5. Submitting token to SheerID...")
            resp = http_client.post(
                f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/step/emailLoop",
                json={'emailToken': token}
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:300]}")
            
            if resp.status_code == 200:
                result = resp.json()
                new_step = result.get('currentStep', 'unknown')
                print(f"   ✅ New step: {new_step}")
        else:
            print("   ❌ Email not received")
        
        mail_client.close()
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        http_client.close()

def test_email_patterns():
    """Test email pattern detection."""
    print("\n" + "=" * 60)
    print("TEST 3: Email Token Pattern Detection")
    print("=" * 60)
    
    # Sample SheerID email patterns
    test_contents = [
        # Pattern 1: URL with emailToken
        'Click here: https://services.sheerid.com/verify/abc123/?verificationId=xyz&emailToken=123456',
        # Pattern 2: 6-digit code
        'Your verification code is: 987654',
        # Pattern 3: HTML with token
        '<a href="https://services.sheerid.com/verify/abc?emailToken=654321">Verify</a>',
        # Pattern 4: Plain number
        'Enter this code: 555123 to verify',
    ]
    
    # Import the extraction method
    mail_client = MailTmClient()
    
    for i, content in enumerate(test_contents):
        print(f"\n{i+1}. Testing: {content[:50]}...")
        
        # Simulate message structure
        fake_msg = {
            'html': [content],
            'text': content
        }
        
        token = mail_client._extract_verification_token(fake_msg)
        
        if token:
            print(f"   ✅ Extracted: {token}")
        else:
            print("   ❌ No token found")
    
    mail_client.close()
    print("\n   ✅ Pattern tests complete")

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MAIL.TM EMAIL LOOP TEST SUITE")
    print("=" * 60)
    
    # Test 1: Basic Mail.tm
    mail_client = test_mail_tm_basic()
    
    if mail_client:
        mail_client.close()
    
    # Test 2: Pattern detection
    test_email_patterns()
    
    # Test 3: Full SheerID flow (interactive)
    print("\n" + "-" * 60)
    run_full = input("\nRun full SheerID email test? (requires verification ID) [y/N]: ")
    
    if run_full.lower() == 'y':
        test_sheerid_email_endpoints()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
