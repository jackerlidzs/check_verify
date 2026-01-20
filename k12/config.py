# SheerID K12 Teacher Verification Config
# Updated to use real K12 schools from SheerID database

# SheerID API Configuration
PROGRAM_ID = '68d47554aa292d20b9bec8f7'
SHEERID_BASE_URL = 'https://services.sheerid.com'
MY_SHEERID_URL = 'https://my.sheerid.com'

# Max file size
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

# Import K12 schools from scraped database
try:
    from .k12_schools_config import K12_SCHOOLS
    SCHOOLS = K12_SCHOOLS
except ImportError:
    # Fallback to hardcoded schools if import fails
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

# Default school - use a well-known K12 school
# The Kinkaid School (Houston, TX) - established K12 school
DEFAULT_SCHOOL_ID = '237830'

# Alternative K12 schools (backup)
ALTERNATIVE_SCHOOL_IDS = [
    '3545593',  # The Spence School (New York, NY)
    '253545',   # Archer School For Girls, The (Los Angeles, CA)
    '262322',   # Bay School Of San Francisco, The (San Francisco, CA)
]

