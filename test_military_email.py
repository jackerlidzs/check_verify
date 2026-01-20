"""Test Military Verification with Email"""
import sys
sys.path.insert(0, '.')

from military.sheerid_verifier import SheerIDVerifier

url = "https://services.sheerid.com/verify/690415d58971e73ca187d8c9/?verificationId=695de3b4c8777b3d5c2b8cd1"
email = "hoanganh22872@gmail.com"

verification_id = SheerIDVerifier.parse_verification_id(url)
print(f"[OK] Verification ID: {verification_id}")
print(f"[OK] Email: {email}")
print()

verifier = SheerIDVerifier(verification_id, email=email)
result = verifier.verify()

print()
print("=" * 60)
print("RESULT:")
print("=" * 60)
print(f"Status: {'SUCCESS' if result['success'] else 'FAILED'}")
print(f"Message: {result['message']}")

if result.get("redirect_url"):
    print(f"Redirect: {result['redirect_url']}")
if result.get("reward_code"):
    print(f"Reward: {result['reward_code']}")
if result.get("current_step"):
    print(f"Current Step: {result['current_step']}")
