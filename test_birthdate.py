"""Test to show birth date format in logs"""
import sys
sys.path.insert(0, '.')

from military.living_veteran_search import get_random_living_veteran
from military.sheerid_verifier import SheerIDVerifier

# Get a random veteran
veteran = get_random_living_veteran()

print("=" * 60)
print("VETERAN DATA GENERATED:")
print("=" * 60)
print(f"First Name:    '{veteran['first_name']}'")
print(f"Last Name:     '{veteran['last_name']}'")
print(f"Birth Date:    '{veteran['birth_date']}'")
print(f"Discharge:     '{veteran['discharge_date']}'")
print(f"Branch:        '{veteran['branch']}'")
print(f"Organization:  {veteran['organization']}")
print()

# Show the exact JSON that will be sent to SheerID
print("=" * 60)
print("REQUEST BODY TO SHEERID (birthDate field):")
print("=" * 60)
body = {
    "firstName": veteran["first_name"],
    "lastName": veteran["last_name"],
    "birthDate": veteran["birth_date"],  # <-- This is the field
    "email": "test@example.com",
    "organization": veteran["organization"],
    "dischargeDate": veteran["discharge_date"],
}

import json
print(json.dumps(body, indent=2))
