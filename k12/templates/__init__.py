"""Template configuration for different schools.

Each school has its own folder with customized templates.
This allows easy switching between schools and avoids detection.
"""
from pathlib import Path
from typing import Dict, Literal

# Available school templates
SchoolTemplate = Literal["nyc_doe", "springfield_high", "miami_dade"]

# School info for each template folder
SCHOOL_TEMPLATES: Dict[str, Dict] = {
    "nyc_doe": {
        "name": "New York City Department of Education",
        "district": "NYC DOE",
        "address": "52 Chambers Street, New York, NY 10007",
        "phone": "(212) 374-0200",
        "website": "www.schools.nyc.gov",
        "email_domain": "schools.nyc.gov",
        "abbreviation": "NYC DOE",
        "state": "NY",
        "ee_id_digits": 7,  # 7-digit Employee ID
        "portal_name": "NYCAPS ESS",
        "payslip_type": "EStub",
        "colors": {
            "primary": "#003399",  # Blue
            "secondary": "#FF6600",  # Orange
            "accent": "#002266",
        }
    },
    "springfield_high": {
        "name": "Springfield High School",
        "district": "Springfield Unified School District", 
        "address": "1234 Education Boulevard, Springfield, TX 75001",
        "phone": "(555) 123-4567",
        "website": "www.springfieldisd.edu",
        "email_domain": "springfieldisd.edu",
        "abbreviation": "SUSD",
        "state": "TX",
        "ee_id_digits": 7,
        "portal_name": "Employee Center",
        "payslip_type": "Standard",
        "colors": {
            "primary": "#003366",  # Navy Blue
            "secondary": "#FFD700",  # Gold
            "accent": "#004488",
        }
    },
    "miami_dade": {
        "name": "Miami-Dade County Public Schools",
        "district": "M-DCPS",
        "address": "1450 NE 2nd Avenue, Miami, FL 33132",
        "phone": "(305) 995-1000",
        "website": "www.dadeschools.net",
        "email_domain": "dadeschools.net",
        "abbreviation": "M-DCPS",
        "state": "FL",
        "ee_id_digits": 6,  # 6-digit Employee ID
        "portal_name": "Employee Portal",
        "payslip_type": "Pay Advice",
        "has_badge_login": True,  # Unique Miami-Dade feature
        "colors": {
            "primary": "#0066CC",  # Blue
            "secondary": "#FFD200",  # Yellow
            "accent": "#00A3E0",  # Light Blue
        }
    },
}

def get_template_path(school: SchoolTemplate, template_name: str) -> Path:
    """Get path to a specific template for a school.
    
    Args:
        school: School folder name (nyc_doe, springfield_high, miami_dade)
        template_name: Template name (id_card, hr_system, payslip, etc.)
        
    Returns:
        Path to the template HTML file
    """
    base_path = Path(__file__).parent / school
    return base_path / f"{template_name}.html"


def get_school_info(school: SchoolTemplate) -> Dict:
    """Get school information for a template folder."""
    return SCHOOL_TEMPLATES.get(school, SCHOOL_TEMPLATES["nyc_doe"])


def list_available_schools() -> list:
    """List all available school templates."""
    return list(SCHOOL_TEMPLATES.keys())
