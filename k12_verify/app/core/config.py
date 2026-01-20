# SheerID K12 Teacher Verification Config
# Standalone version for k12_verify project

# SheerID API Configuration
PROGRAM_ID = '68d47554aa292d20b9bec8f7'
SHEERID_BASE_URL = 'https://services.sheerid.com'
MY_SHEERID_URL = 'https://my.sheerid.com'

# Max file size
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

# Default K12 schools
SCHOOLS = {
    '237830': {
        'id': 237830,
        'idExtended': '237830',
        'name': 'The Kinkaid School',
        'city': 'Houston',
        'state': 'TX',
        'country': 'US',
        'type': 'K12'
    },
    '3545593': {
        'id': 3545593,
        'idExtended': '3545593',
        'name': 'The Spence School',
        'city': 'New York',
        'state': 'NY',
        'country': 'US',
        'type': 'K12'
    },
    '253545': {
        'id': 253545,
        'idExtended': '253545',
        'name': 'Archer School For Girls, The',
        'city': 'Los Angeles',
        'state': 'CA',
        'country': 'US',
        'type': 'K12'
    },
}

# Default school
DEFAULT_SCHOOL_ID = '237830'

# Alternative K12 schools
ALTERNATIVE_SCHOOL_IDS = [
    '3545593',
    '253545',
    '262322',
]


import random

def get_random_k12_school() -> dict:
    """Get a random school that is type K12 (not HIGH_SCHOOL)."""
    k12_schools = [s for s in SCHOOLS.values() if s.get('type') == 'K12']
    if k12_schools:
        return random.choice(k12_schools)
    return SCHOOLS[DEFAULT_SCHOOL_ID]


def is_valid_k12_school(school: dict) -> bool:
    """Check if school is a valid K12 type (not HIGH_SCHOOL or other)."""
    school_type = school.get('type', '').upper()
    # K12 is good, HIGH_SCHOOL and UNIVERSITY are not
    return school_type in ['K12', 'K-12', 'K_12']


def get_school_by_id(school_id: str) -> dict:
    """Get school by ID, return default if not found."""
    return SCHOOLS.get(str(school_id), SCHOOLS[DEFAULT_SCHOOL_ID])

