"""Test Military Verification with Rare Profile"""
import sys
sys.path.insert(0, '.')

from military.sheerid_verifier import SheerIDVerifier
from military import config

url = "https://services.sheerid.com/verify/690415d58971e73ca187d8c9/?verificationId=695de5f211d2fc54d0368ec9"
email = "hoanganh22872@gmail.com"

# Use rare Coast Guard veteran
veteran_info = {
    "first_name": "Allen",
    "last_name": "Goldberg",
    "birth_date": "1937-01-26",
    "discharge_date": "2025-03-15",
    "organization": {"id": 4074, "name": "Coast Guard"},
    "branch": "US COAST GUARD"
}

verification_id = SheerIDVerifier.parse_verification_id(url)
print(f"[OK] Verification ID: {verification_id}")
print(f"[OK] Email: {email}")
print(f"[OK] Veteran: {veteran_info['first_name']} {veteran_info['last_name']} (Coast Guard)")
print()

verifier = SheerIDVerifier(verification_id, email=email)

# Override generate_veteran_info to use our specific veteran
import military.name_generator as ng
original_func = ng.generate_veteran_info
ng.generate_veteran_info = lambda: veteran_info

result = verifier.verify()

ng.generate_veteran_info = original_func

print()
print("=" * 60)
print("RESULT:")
print("=" * 60)
print(f"Status: {'SUCCESS' if result['success'] else 'FAILED'}")
print(f"Message: {result['message']}")

if result.get("redirect_url"):
    print(f"Redirect: {result['redirect_url']}")
if result.get("current_step"):
    print(f"Current Step: {result['current_step']}")
if result.get("suggested_action"):
    print(f"Action: {result['suggested_action']}")
