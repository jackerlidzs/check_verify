from k12.browser_verifier import BrowserVerifier, logger
import time
import logging

# Configure logging to see details
logging.basicConfig(level=logging.INFO)

# Override constants in browser_verifier for testing
import k12.browser_verifier as bv
bv.SHEERID_VERIFY_URL = "http://localhost:5000/verify/68d47554aa292d20b9bec8f7/"
bv.SHEERID_BASE_URL = "http://localhost:5000"

def test_mock_verification():
    print("Starting Mock Browser Verification")
    print(f"Target URL: {bv.SHEERID_VERIFY_URL}")
    
    # Run in HEADED mode so user can see it
    verifier = BrowserVerifier(headless=False)
    
    try:
        result = verifier.verify()
        print("\nVerification Result:")
        print(result)
        
    except Exception as e:
        print(f"\nTest Failed: {e}")

if __name__ == "__main__":
    test_mock_verification()
