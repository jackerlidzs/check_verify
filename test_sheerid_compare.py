"""Compare current code with SheerID requirements"""
import sys
sys.path.insert(0, '.')
import json

from military.living_veteran_search import get_random_living_veteran

# Get sample veteran data
veteran = get_random_living_veteran()

print("=" * 70)
print("SHEERID REQUIRED FORMAT (from documentation)")
print("=" * 70)

sheerid_required = {
    "firstName": "name",
    "lastName": "name",
    "birthDate": "1939-12-01",        # YYYY-MM-DD
    "email": "your mail",
    "phoneNumber": "",
    "organization": {
        "id": 4070,
        "name": "Army"
    },
    "dischargeDate": "2025-05-29",    # YYYY-MM-DD
    "locale": "en-US",
    "country": "US",
    "metadata": {
        "marketConsentValue": False,
        "refererUrl": "",
        "verificationId": "",
        "flags": "...",
        "submissionOptIn": "..."
    }
}
print(json.dumps(sheerid_required, indent=2))

print()
print("=" * 70)
print("OUR CODE GENERATES (actual)")
print("=" * 70)

our_data = {
    "firstName": veteran["first_name"],
    "lastName": veteran["last_name"],
    "birthDate": veteran["birth_date"],
    "email": "vet12345@airsworld.net",
    "phoneNumber": "",
    "organization": {
        "id": veteran["organization"]["id"],
        "name": veteran["organization"]["name"]
    },
    "dischargeDate": veteran["discharge_date"],
    "locale": "en-US",
    "country": "US",
    "metadata": {
        "marketConsentValue": False,
        "refererUrl": "",
        "verificationId": "xxx",
        "flags": "...",
        "submissionOptIn": "..."
    }
}
print(json.dumps(our_data, indent=2))

print()
print("=" * 70)
print("FIELD-BY-FIELD COMPARISON")
print("=" * 70)

checks = [
    ("firstName", "String", veteran["first_name"], "name"),
    ("lastName", "String", veteran["last_name"], "name"),
    ("birthDate", "YYYY-MM-DD", veteran["birth_date"], "1939-12-01"),
    ("email", "Email", "vet12345@airsworld.net", "your mail"),
    ("phoneNumber", "String (empty)", "", ""),
    ("organization.id", "Integer", veteran["organization"]["id"], 4070),
    ("organization.name", "String", veteran["organization"]["name"], "Army"),
    ("dischargeDate", "YYYY-MM-DD", veteran["discharge_date"], "2025-05-29"),
    ("locale", "String", "en-US", "en-US"),
    ("country", "String", "US", "US"),
]

import re
for field, expected_format, our_value, example in checks:
    status = "OK"
    
    # Check specific formats
    if "YYYY-MM-DD" in expected_format:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(our_value)):
            status = "FAIL - wrong date format"
    elif field == "organization.id":
        if our_value not in [4070, 4071, 4072, 4073, 4074, 4544268]:
            status = "FAIL - invalid org ID"
    
    print(f"  {field:20} | Format: {expected_format:15} | Value: {our_value!r:25} | {status}")
