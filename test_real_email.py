"""Test Military Verification with Real Email"""
import sys
sys.path.insert(0, '.')

from military.sheerid_verifier import SheerIDVerifier

url = "PASTE_NEW_URL_HERE"  # User will paste new URL
email = "hoanganh22872@gmail.com"  # Real email

verification_id = SheerIDVerifier.parse_verification_id(url)
print(f"[OK] Verification ID: {verification_id}")
print(f"[OK] Email: {email}")
print()

# Use living veteran but with real email
verifier = SheerIDVerifier(verification_id, email=email, use_living_veteran=True)
result = verifier.verify()

print()
print("=" * 60)
print("RESULT:")
print("=" * 60)
print(f"Status: {'SUCCESS' if result['success'] else 'FAILED'}")
print(f"Message: {result['message']}")

if result.get("current_step") == "emailLoop":
    print()
    print("[!] Check your Gmail for verification link from SheerID!")
    print("[!] The email token will come to: hoanganh22872@gmail.com")
