"""Test with custom email"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.core.browser_verifier_sync import run_sync_verification
from app.core.name_generator import generate_teacher_info
from app.core import config
from app import config as app_config
import random

URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=6959d240dc2d116d71eb8272&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"
EMAIL = "effryeannon33@bjedu.tech"

def log(step, msg):
    print(f"[{step}] {msg}")

# Generate teacher
DISTRICT_TEMPLATES = list(app_config.DISTRICTS.keys())
district = random.choice(DISTRICT_TEMPLATES)
teacher = generate_teacher_info(district=district)

school_id = teacher.get('school_id', config.DEFAULT_SCHOOL_ID)
school = config.SCHOOLS.get(str(school_id), config.SCHOOLS[config.DEFAULT_SCHOOL_ID])

teacher_data = {
    'first_name': teacher['first_name'],
    'last_name': teacher['last_name'],
    'email': EMAIL,  # Use custom email
    'birth_date': teacher['birth_date'],
    'school_name': teacher.get('school_name') or school['name'],
}

print(f"Teacher: {teacher_data['first_name']} {teacher_data['last_name']}")
print(f"Email: {EMAIL}")
print(f"School: {school['name']}")
print()

# Run verification
result = run_sync_verification(
    sheerid_url=URL,
    teacher_data=teacher_data,
    school=school,
    proxy_config=None,  # No proxy for test
    status_callback=log,
    headless=False  # Show browser for debugging
)

print()
print("="*50)
print(f"Success: {result.get('success')}")
print(f"URL: {result.get('redirectUrl', 'N/A')}")
print(f"Message: {result.get('message', 'N/A')}")
