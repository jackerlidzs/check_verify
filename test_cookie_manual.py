import json
import logging
from k12.cookie_verifier import CookieVerifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_manual_verification():
    # User provided data - FRESH COOKIES 2026-01-01
    cookies_json = """
[
    {
        "domain": "services.sheerid.com",
        "hostOnly": true,
        "httpOnly": true,
        "name": "JSESSIONID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": true,
        "storeId": null,
        "value": "GqNujSnlkqFX4x9n_Fh0fYc2wBMrEx8rZpqxsynZqb5Dr4PLm25nmx3AM40VTQ_kio5T2B9_12Gb8-MMU6m6HnlDwXjuGL9jK4BGOY77o-yXYcnnwYZGjIYmnybMnizZuGmfHQ__.core-platform-sheerid-84f54cc6bf-scpsd"
    },
    {
        "domain": "services.sheerid.com",
        "expirationDate": 1767811975.851119,
        "hostOnly": true,
        "httpOnly": false,
        "name": "AWSALBCORS",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "9qJLMT4GRGAig1J39IxO68zcnDHPPQeUrUbzO/4lp8hiSYWOU6f2IKPjIwWCULx+2x4gUbmWxc5e/96UYeYzmpsfdGbRG1jZr5+i0BAwGpngP7LhHxSKaHiUXacJ"
    },
    {
        "domain": "services.sheerid.com",
        "expirationDate": 1767811989,
        "hostOnly": true,
        "httpOnly": false,
        "name": "sid-verificationId",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "6955711356f980215a14f992"
    }
]
    """
    
    print("Testing Manual Cookie Verification")
    print("Fresh cookies from 2026-01-01")
    
    try:
        # Parse cookies
        cookie_list = json.loads(cookies_json)
        cookies = {}
        for c in cookie_list:
            if c.get('name') and c.get('value'):
                cookies[c['name']] = c['value']
        
        print(f"Extracted {len(cookies)} cookies")
        print(f"Verification ID: {cookies.get('sid-verificationId')}")
        
        # Initialize Verifier
        verifier = CookieVerifier(cookies)
        
        # Run Verification
        result = verifier.verify()
        
        print("\nVerification Result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_verification()
