"""Test Military Verification - No Emoji Version"""
import sys
sys.path.insert(0, '.')

from military.sheerid_verifier import SheerIDVerifier

url = sys.argv[1] if len(sys.argv) > 1 else input("Enter URL: ")
verification_id = SheerIDVerifier.parse_verification_id(url)

if not verification_id:
    print("[ERROR] Invalid verification ID")
    sys.exit(1)

print(f"[OK] Verification ID: {verification_id}")
print()

verifier = SheerIDVerifier(verification_id)
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
if result.get("suggested_action"):
    print(f"Action: {result['suggested_action']}")
    print(f"Hint: {result.get('action_message', '')}")
