"""Military Verification Configuration"""

# SheerID API settings
SHEERID_BASE_URL = 'https://services.sheerid.com'

# Military Status for veterans
MILITARY_STATUS = "VETERAN"

# Military Organization Mapping
# Maps branch names from data file to SheerID organization info
ORGANIZATIONS = {
    "US AIR FORCE": {
        "id": 4073,
        "name": "Air Force"
    },
    "US ARMY": {
        "id": 4070,
        "name": "Army"
    },
    "US NAVY": {
        "id": 4072,
        "name": "Navy"
    },
    "US MARINE CORPS": {
        "id": 4071,
        "name": "Marine Corps"
    },
    "US COAST GUARD": {
        "id": 4074,
        "name": "Coast Guard"
    },
    "US SPACE FORCE": {
        "id": 4544268,
        "name": "Space Force"
    }
}

# Default organization if branch is empty or not found
DEFAULT_ORGANIZATION = {
    "id": 4070,
    "name": "Army"
}

# Data file path (relative to this module)
DATA_FILE = "data/vlm_2025_profiles.jsonl"
