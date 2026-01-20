"""K12 Teacher Document Generator (Synchronized Templates)

Generates teacher verification documents with consistent data:
1. Employee Access Center (HR System screenshot)
2. School ID Card (Faculty ID)
3. Payslip (Pay Statement)
4. Employment Verification Letter
5. Job Offer Letter
6. White/Blank Image (for reset trick)

All documents share the SAME Employee ID and school info for consistency.
Templates are organized by school folder for easy customization.
"""
import random
import base64
import httpx
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional

from xhtml2pdf import pisa

# Import template config
from .templates import SchoolTemplate, SCHOOL_TEMPLATES, get_template_path, get_school_info, list_available_schools


# ============================================================================
# AVATAR GENERATION - Makes ID cards look realistic
# ============================================================================

def _get_avatar_base64(first_name: str, last_name: str) -> str:
    """
    Generate a professional avatar using UI Avatars API.
    Returns base64 encoded image data for embedding in HTML.
    """
    try:
        # Random background colors (professional tones)
        bg_colors = ["0D8ABC", "2E86AB", "A23B72", "F18F01", "C73E1D", "3A7D44", "5C4D7D"]
        bg = random.choice(bg_colors)
        
        # UI Avatars API - generates initials-based avatars
        url = f"https://ui-avatars.com/api/?name={first_name}+{last_name}&background={bg}&color=fff&size=200&bold=true&format=png"
        
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"Avatar fetch failed: {e}")
    
    # Fallback: return empty (template will show placeholder)
    return ""


def _add_camera_effects(png_bytes: bytes) -> bytes:
    """
    Add realistic camera effects to make document look like a photo.
    - Slight rotation
    - Brightness variation
    - Minor blur
    - JPEG compression artifacts
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import io
        
        # Load image
        img = Image.open(io.BytesIO(png_bytes))
        
        # 1. Slight rotation (-2 to +2 degrees)
        rotation = random.uniform(-2, 2)
        img = img.rotate(rotation, expand=True, fillcolor=(255, 255, 255))
        
        # 2. Brightness variation (95-105%)
        brightness = random.uniform(0.95, 1.05)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)
        
        # 3. Contrast variation (95-105%)
        contrast = random.uniform(0.95, 1.05)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
        
        # 4. Minor blur (simulates camera focus)
        if random.random() < 0.3:  # 30% chance
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # 5. Save as JPEG with slight compression (adds artifacts like real photo)
        output = io.BytesIO()
        quality = random.randint(85, 95)
        img = img.convert('RGB')  # JPEG doesn't support transparency
        img.save(output, format='JPEG', quality=quality)
        
        return output.getvalue()
        
    except ImportError:
        print("Pillow not installed, skipping camera effects")
        return png_bytes
    except Exception as e:
        print(f"Camera effects failed: {e}")
        return png_bytes

# Document type enum - local templates
DocumentType = Literal["hr_system", "id_card", "payslip", "verification_letter", "offer_letter", "blank"]

# Default school template
DEFAULT_SCHOOL_TEMPLATE: SchoolTemplate = "nyc_doe"

# Salary ranges with Step/Lane system (realistic K12 teacher salaries)
SALARY_RANGES = [
    ("Step 1, BA", 45000, 52000),
    ("Step 2, BA", 48000, 55000),
    ("Step 3, BA+15", 52000, 60000),
    ("Step 4, BA+30", 55000, 65000),
    ("Step 5, BA+30", 58000, 68000),
    ("Step 6, MA", 62000, 72000),
    ("Step 7, MA+15", 65000, 78000),
    ("Step 8, MA+30", 70000, 85000),
    ("Step 9, MA+45", 75000, 90000),
    ("Step 10, Doctorate", 80000, 95000),
]

def get_random_school_template() -> SchoolTemplate:
    """Return a random school template."""
    return random.choice(list_available_schools())

# Position/Job Title options for randomization (K-12 staff types)
POSITIONS = [
    # Teachers
    "Faculty - Science Department (FTE 1.0)",
    "Faculty - Mathematics Department (FTE 1.0)",
    "Faculty - English / Language Arts (FTE 1.0)",
    "Elementary Classroom Teacher (FTE 1.0)",
    "Faculty - Social Studies (FTE 1.0)",
    "Special Education Teacher (FTE 1.0)",
    "Faculty - Physical Education (FTE 1.0)",
    "Faculty - Art Department (FTE 1.0)",
    "Faculty - Music Department (FTE 1.0)",
    "Reading Specialist (FTE 1.0)",
    "ESL/ESOL Teacher (FTE 1.0)",
    "Faculty - Technology Education (FTE 1.0)",
    # Administrators
    "Assistant Principal",
    "Dean of Students",
    "Department Chair - Science",
    "Department Chair - Mathematics",
    "Instructional Coach",
    "Curriculum Coordinator",
    # Counselors & Support Staff
    "School Counselor",
    "Guidance Counselor",
    "School Psychologist",
    "Social Worker",
    # Specialists
    "Speech-Language Pathologist",
    "Occupational Therapist",
    "Library Media Specialist",
    "Technology Integration Specialist",
]

DEPARTMENTS = [
    "Science Department",
    "Mathematics Department",
    "English Department",
    "Social Studies",
    "Physical Education",
    "Art Department",
    "Music Department",
    "Special Education",
]


# ============================================================================
# SHARED DATA GENERATOR - Ensures all documents have same info
# ============================================================================

class TeacherDocumentData:
    """Holds synchronized data for all document types.
    
    Create once, then pass to all document generators to ensure:
    - Same Employee ID across all docs
    - Same school name/district across all docs
    - Same hire date, department, etc.
    """
    
    def __init__(self, first_name: str, last_name: str, school_name: str = None, 
                 school_template: SchoolTemplate = None, position: str = None, 
                 hire_date: str = None, email: str = None,
                 employee_id: str = None, annual_salary: int = None,
                 salary_step: str = None, department: str = None,
                 pension_number: str = None):
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = f"{first_name} {last_name}"
        
        # Get school template and info
        self.school_template = school_template or get_random_school_template()
        school_info = get_school_info(self.school_template)
        
        # School info from config
        self.district_name = school_info["name"]
        self.district_short = school_info.get("district", school_info["abbreviation"])
        self.district_abbreviation = school_info["abbreviation"]
        self.address = school_info["address"]
        self.phone = school_info["phone"]
        self.website = school_info["website"]
        self.state = school_info["state"]
        self.portal_name = school_info.get("portal_name", "Employee Portal")
        self.payslip_type = school_info.get("payslip_type", "Standard")
        self.email_domain = school_info.get("email_domain", "school.edu")
        
        # School name (can be overridden or use from school list)
        self.school_name = school_name or self._generate_school_name()
        self.district_logo = self._generate_district_logo()
        
        # Generate avatar for ID card
        self.avatar_base64 = _get_avatar_base64(first_name, last_name)
        
        # Employee ID - USE PROVIDED or generate with district-specific digit count
        if employee_id:
            self.employee_id = int(employee_id) if isinstance(employee_id, str) else employee_id
            self.employee_id_formatted = f"E-{self.employee_id}"
        else:
            # Use district-specific digit count from config
            digits = school_info.get("ee_id_digits", 7)  # NYC=7, Miami=6, Springfield=7
            self.employee_id = random.randint(10**(digits-1), 10**digits - 1)
            self.employee_id_formatted = f"E-{self.employee_id}"
        
        # Pension number - USE PROVIDED or generate
        self.pension_num = pension_number or f"TRS-{self.employee_id}"
        
        # NYC-specific fields
        self.payroll_number = f"{random.randint(1, 99):03d}"
        self.work_unit = f"M{random.randint(1, 999):03d}"
        self.distribution_code = f"D{random.randint(100, 999)}"
        
        # Miami-specific fields
        if school_info.get("has_badge_login"):
            self.badge_login = f"BADGE-{self.employee_id}"
            self.badge_status = "ACTIVE"
        else:
            self.badge_login = None
            self.badge_status = None
        
        # Salary - USE PROVIDED or generate with Step/Lane
        if annual_salary and salary_step:
            self.salary_step = salary_step
            self.annual_salary = annual_salary
        else:
            salary_info = random.choice(SALARY_RANGES)
            self.salary_step = salary_info[0]
            self.annual_salary = random.randint(salary_info[1], salary_info[2])
        self.salary_formatted = f"${self.annual_salary:,.2f} ({self.salary_step})"
        
        # Position/department - USE PROVIDED or random
        self.position = position or random.choice(POSITIONS)
        self.department = department or random.choice(DEPARTMENTS)
        
        # Dates - Use provided hire_date or generate
        self.hire_date = hire_date or self._generate_hire_date()
        
        # Fixed academic year: 2026-2028
        self.start_year = 2026
        self.end_year = 2028
        self.academic_year = "2026-2028"
        
        # Generate assignment dates with fixed years
        start_day = random.randint(12, 25)
        end_month = "May" if random.random() < 0.4 else "June"
        end_day = random.randint(20, 31) if end_month == "May" else random.randint(1, 15)
        self.assignment_dates = f"August {start_day}, 2026 - {end_month} {end_day}, 2028"
        
        self.pay_period, self.pay_date = self._generate_pay_period()
        
        # Start date (August 2026)
        start_day = random.randint(10, 25)
        self.start_date = f"August {start_day}, 2026"
        self.contract_period = "2026-2028 Academic Year"
        
        # ID Card dates
        now = datetime.now()
        issue_year = random.choice([2025, 2026])  # Recent issue date
        self.issue_date = f"{random.randint(1, 12):02d}/15/{issue_year}"
        self.valid_date = "06/30/2028"  # Valid until June 2028
        self.school_year = "2026-28"  # Display format for ID card
        
        # Reference/Document numbers
        self.ref_number = f"HR/OFFER/{now.year}/{random.randint(100000, 999999)}"
        self.document_id = f"OFR-{now.year}-{random.randint(1000000, 9999999)}"
        
        # Current timestamp
        self.current_date = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        self.print_date = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
        self.letter_date = datetime.now().strftime("%B %d, %Y")
        
        # School email address (firstname.lastname@school.edu)
        self.school_email = f"{first_name.lower()}.{last_name.lower()}@{self.email_domain}"
    
    def _generate_school_name(self) -> str:
        """Generate a realistic school name."""
        school_names = [
            "Lincoln High School", "Roosevelt Middle School", "Washington Elementary",
            "Jefferson Academy", "Franklin School", "Kennedy High School",
            "Madison Middle School", "Adams Elementary", "Monroe Academy",
            "Hamilton High School", "Jackson Middle School", "Wilson Elementary",
        ]
        return random.choice(school_names)
    
    def _generate_district_logo(self) -> str:
        """Generate abbreviation for logo."""
        # Use district abbreviation from school info
        return self.district_abbreviation
    
    def _get_academic_year(self) -> tuple:
        now = datetime.now()
        if now.month < 8:
            start_year = now.year - 1
            end_year = now.year
        else:
            start_year = now.year
            end_year = now.year + 1
        return f"{start_year}-{end_year}", start_year, end_year
    
    def _generate_hire_date(self) -> str:
        current_year = datetime.now().year
        hire_year = random.randint(current_year - 12, current_year - 1)
        if random.random() < 0.85:
            return f"August {random.randint(1, 20)}, {hire_year}"
        return f"January {random.randint(2, 15)}, {hire_year}"
    
    def _generate_assignment_dates(self) -> str:
        start_day = random.randint(12, 25)
        if random.random() < 0.4:
            return f"August {start_day}, {self.start_year} - May {random.randint(20, 31)}, {self.end_year}"
        return f"August {start_day}, {self.start_year} - June {random.randint(1, 15)}, {self.end_year}"
    
    def _generate_pay_period(self) -> tuple:
        """Generate realistic pay period and pay date.
        
        US K-12 schools typically pay bi-weekly or semi-monthly.
        Payslip shows PREVIOUS (completed) pay period, not current/future.
        
        Semi-monthly schedule:
        - Period 1: 1st-15th → Pay date: 20th same month
        - Period 2: 16th-end → Pay date: 5th next month
        """
        from calendar import monthrange
        now = datetime.now()
        
        # Generate pay period from PREVIOUS cycle (not current)
        if now.day <= 5:
            # We're in early month - show previous month's 2nd period (16-end)
            prev_month = now.month - 1 if now.month > 1 else 12
            prev_year = now.year if now.month > 1 else now.year - 1
            last_day = monthrange(prev_year, prev_month)[1]
            start_day, end_day = 16, last_day
            pay_month, pay_year = now.month, now.year
            pay_day = min(now.day, 5)  # Pay date in early current month
        elif now.day <= 20:
            # We're mid-month - show current month's 1st period (1-15)
            prev_month = now.month
            prev_year = now.year
            start_day, end_day = 1, 15
            pay_month, pay_year = now.month, now.year
            pay_day = min(now.day, 20)  # Pay date around 20th
        else:
            # We're late month - show current month's 1st period (1-15)
            prev_month = now.month
            prev_year = now.year
            start_day, end_day = 1, 15
            pay_month, pay_year = now.month, now.year
            pay_day = 20  # Standard pay date

        period = f"{prev_month:02d}/{start_day:02d}/{prev_year} - {prev_month:02d}/{end_day:02d}/{prev_year}"
        pay_date = f"{pay_month:02d}/{pay_day:02d}/{pay_year}"
        
        return period, pay_date


# ============================================================================
# TEMPLATE RENDERERS
# ============================================================================

def _render_hr_template(data: TeacherDocumentData, school_template: SchoolTemplate = None) -> str:
    """Render Employee Access Center (HR System) template."""
    school = school_template or data.school_template
    template_path = get_template_path(school, "hr_system")
    html = template_path.read_text(encoding="utf-8")

    # Color replacements
    color_map = {
        "var(--primary-blue)": "#0056b3",
        "var(--border-gray)": "#dee2e6",
        "var(--bg-gray)": "#f8f9fa",
    }
    for placeholder, color in color_map.items():
        html = html.replace(placeholder, color)

    # Replace template values with synchronized data
    html = html.replace("Sarah J. Connor", data.full_name)
    html = html.replace("E-9928104", data.employee_id_formatted)
    html = html.replace('id="currentDate"></span>', f'id="currentDate">{data.current_date}</span>')
    html = html.replace("Springfield School District - Employee Access Center", 
                       f"{data.district_name} - Employee Access Center")
    html = html.replace("Springfield North High School", data.school_name)
    html = html.replace(">SD<", f">{data.district_logo}<")
    html = html.replace("Faculty - Science Department (FTE 1.0)", data.position)
    html = html.replace("August 15, 2018", data.hire_date)
    html = html.replace("2025-2026", data.academic_year)
    html = html.replace("August 20, 2025 - June 10, 2026", data.assignment_dates)

    return html


def _render_id_card_template(data: TeacherDocumentData, school_template: SchoolTemplate = None) -> str:
    """Render School ID Card template."""
    school = school_template or data.school_template
    template_path = get_template_path(school, "id_card")
    html = template_path.read_text(encoding="utf-8")

    # Short position for badge
    position_short = data.position.split(" - ")[0] if " - " in data.position else data.position
    if "(" in position_short:  # Remove "(FTE 1.0)" etc
        position_short = position_short.split("(")[0].strip()
    
    # Department short name
    department_short = data.department.replace(" Department", "")
    
    # Replace template values
    html = html.replace("Sarah J. Connor", data.full_name)
    
    # Replace BOTH 6-digit (Miami-Dade) and 7-digit (NYC DOE) placeholders
    html = html.replace(">123456<", f">{data.employee_id}<")  # Miami-Dade format
    html = html.replace("*123456*", f"*{data.employee_id}*")  # Miami-Dade barcode
    html = html.replace("ID# 123456", f"ID# {data.employee_id}")  # Miami-Dade footer
    html = html.replace(">1234567<", f">{data.employee_id}<")  # NYC DOE format
    html = html.replace("*1234567*", f"*{data.employee_id}*")  # NYC DOE barcode
    
    # District info
    html = html.replace("Miami-Dade County Public Schools", data.district_name)
    html = html.replace("New York City Department of Education", data.district_name)
    html = html.replace("NYC DOE", data.district_abbreviation)
    html = html.replace("NYC<br>DOE", f"{data.district_abbreviation[:2]}<br>{data.district_abbreviation[2:] if len(data.district_abbreviation) > 2 else data.district_abbreviation}")
    
    # School, department, position
    html = html.replace("PS 123 Manhattan", data.school_name)
    html = html.replace(">Science<", f">{department_short}<")
    html = html.replace("Science Teacher", data.position)
    html = html.replace(">Teacher<", f">{position_short}<")
    
    # Dates
    html = html.replace("2024-25", data.school_year)
    html = html.replace("09/01/2024", data.issue_date)
    html = html.replace("08/15/2018", data.hire_date)
    html = html.replace("Issued: 09/01/2024", f"Issued: {data.issue_date}")
    
    # Avatar - Replace placeholder with actual image
    if data.avatar_base64:
        # Replace photo placeholder with embedded image
        avatar_html = f'<img src="data:image/png;base64,{data.avatar_base64}" style="width:100%;height:100%;object-fit:cover;border-radius:4px;">'
        html = html.replace("EMPLOYEE<br>PHOTO", avatar_html)
        html = html.replace("EMPLOYEE\n                <br>PHOTO", avatar_html)

    return html


def _render_payslip_template(data: TeacherDocumentData, school_template: SchoolTemplate = None) -> str:
    """Render Payslip (NYCAPS ESS style) template."""
    school = school_template or data.school_template
    template_path = get_template_path(school, "payslip")
    html = template_path.read_text(encoding="utf-8")

    # Pay period end date
    pay_period_end = data.pay_period.split(" - ")[1] if " - " in data.pay_period else "12/14/2025"
    
    # Replace template values
    html = html.replace("CONNOR, SARAH J", f"{data.last_name.upper()}, {data.first_name.upper()}")
    html = html.replace("12/20/2025 10:34:22 AM", data.print_date)
    
    # Employee ID - support all district formats:
    # NYC DOE: 7 digits (1234567)
    # Miami-Dade: 6 digits (123456)
    # Springfield: 7 digits (1234567)
    html = html.replace(">123456<", f">{data.employee_id}<")  # 6-digit Miami-Dade
    html = html.replace(">1234567<", f">{data.employee_id}<")  # 7-digit NYC/Springfield
    html = html.replace(">E12345678<", f">{data.employee_id_formatted}<")  # Legacy E prefix format
    html = html.replace("2025-24-12345678", f"2025-24-{data.employee_id}")  # Advice number
    html = html.replace("2025-24-123456", f"2025-24-{data.employee_id}")  # Advice number 6-digit
    
    html = html.replace("TRS-9876543", data.pension_num)
    html = html.replace("12/01/2025 - 12/14/2025", data.pay_period)
    html = html.replace("12/14/2025", pay_period_end)
    html = html.replace("12/20/2025", data.pay_date)
    
    # Location - replace with actual school name
    html = html.replace("PS 123 Manhattan", data.school_name)
    
    # District Name - replace for all district templates
    html = html.replace("Miami-Dade County Public Schools", data.district_name)
    html = html.replace("New York City Department of Education", data.district_name)
    html = html.replace("Springfield Unified School District", data.district_name)
    html = html.replace("M-DCPS", data.district_abbreviation)
    html = html.replace(">NYC DOE<", f">{data.district_abbreviation}<")

    return html


def _render_verification_letter_template(data: TeacherDocumentData, school_template: SchoolTemplate = None) -> str:
    """Render Employment Verification Letter template."""
    school = school_template or data.school_template
    template_path = get_template_path(school, "verification_letter")
    html = template_path.read_text(encoding="utf-8")
    
    # Current date formatted
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    print_date = datetime.now().strftime("%m/%d/%Y")
    
    # District info
    district_upper = data.district_name.upper()
    district_abbrev = "".join([word[0] for word in data.district_name.split()[:3]]).upper()
    
    # Generate HR Director name
    hr_directors = ["Dr. Michael Thompson", "Dr. Sarah Williams", "Mr. James Anderson", 
                    "Ms. Patricia Moore", "Dr. Robert Martinez", "Mrs. Jennifer Garcia"]
    hr_director = random.choice(hr_directors)
    
    # Replace template values
    html = html.replace("SPRINGFIELD UNIFIED SCHOOL DISTRICT", district_upper)
    html = html.replace("Springfield Unified School District", data.district_name)
    html = html.replace("Sarah J. Connor", data.full_name)
    html = html.replace("E-1234567", data.employee_id_formatted)
    html = html.replace("Faculty - Science Department (FTE 1.0)", data.position)
    html = html.replace("Springfield North High School", data.school_name)
    html = html.replace("August 15, 2018", data.hire_date)
    html = html.replace(">December 27, 2024<", f">{current_date}<")
    html = html.replace(">12/27/2024<", f">{print_date}<")
    html = html.replace("Dr. Michael Thompson", hr_director)
    html = html.replace(">SUSD<", f">{district_abbrev}<")
    
    return html



def _render_offer_letter_template(data: TeacherDocumentData, school_template: SchoolTemplate = None) -> str:
    """Render Job Offer Letter template."""
    # Use school template from data or parameter
    school = school_template or data.school_template
    template_path = get_template_path(school, "offer_letter")
    html = template_path.read_text(encoding="utf-8")
    
    # District info
    district_upper = data.district_name.upper()
    
    # Position short name (for offer box title)
    position_short = data.position.split(" - ")[1].split(" (")[0] if " - " in data.position else "Teacher"
    
    # Replace template values with data from TeacherDocumentData
    html = html.replace("SPRINGFIELD UNIFIED SCHOOL DISTRICT", district_upper)
    html = html.replace("NEW YORK CITY DEPARTMENT OF EDUCATION", district_upper)
    html = html.replace("MIAMI-DADE COUNTY PUBLIC SCHOOLS", district_upper)
    html = html.replace("Springfield Unified School District", data.district_name)
    html = html.replace("New York City Department of Education", data.district_name)
    html = html.replace("Miami-Dade County Public Schools", data.district_name)
    
    # Address, Phone, Website
    html = html.replace("52 Chambers Street, New York, NY 10007", data.address)
    html = html.replace("1450 NE 2nd Avenue, Miami, FL 33132", data.address)
    html = html.replace("1234 Education Boulevard, Springfield, TX 75001", data.address)
    html = html.replace("(212) 374-0200", data.phone)
    html = html.replace("(305) 995-1000", data.phone)
    html = html.replace("(555) 123-4567", data.phone)
    html = html.replace("www.schools.nyc.gov", data.website)
    html = html.replace("www.dadeschools.net", data.website)
    html = html.replace("www.springfieldisd.edu", data.website)
    
    # Employee info
    html = html.replace("Sarah J. Connor", data.full_name)
    html = html.replace("E-1234567", data.employee_id_formatted)
    html = html.replace("E-123456", data.employee_id_formatted)
    html = html.replace("Faculty - Science Department (FTE 1.0)", data.position)
    html = html.replace("Faculty - Science Department", f"Faculty - {position_short}")
    html = html.replace("Springfield North High School", data.school_name)
    
    # NYC-specific
    html = html.replace(">040<", f">{data.payroll_number}<")
    html = html.replace(">M015<", f">{data.work_unit}<")
    
    # Dates
    html = html.replace("December 27, 2024", data.letter_date)
    html = html.replace("August 15, 2024", data.start_date)
    html = html.replace("2024-2025 Academic Year", data.contract_period)
    
    # Salary
    html = html.replace("$58,500.00 (Step 5, BA+30)", data.salary_formatted)
    
    # Reference numbers
    html = html.replace("HR/OFFER/2024/1234567", data.ref_number)
    html = html.replace("HR/OFFER/2024/123456", data.ref_number)
    html = html.replace("OFR-2024-1234567", data.document_id)
    html = html.replace("OFR-2024-123456", data.document_id)
    
    return html

def generate_blank_image() -> bytes:
    """Generate a blank white image."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright required") from exc

    html = """
    <!DOCTYPE html>
    <html>
    <head><style>body { margin: 0; background: white; }</style></head>
    <body><div style="width: 800px; height: 600px; background: white;"></div></body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 800, "height": 600})
        page.set_content(html, wait_until="load")
        png_bytes = page.screenshot(type="png")
        browser.close()

    return png_bytes


# ============================================================================
# MAIN GENERATOR FUNCTIONS
# ============================================================================

def generate_teacher_png(first_name: str, last_name: str, school_name: str = None,
                         doc_type: DocumentType = "id_card",
                         shared_data: TeacherDocumentData = None,
                         school_template: SchoolTemplate = None) -> bytes:
    """
    Generate teacher document as PNG image.
    
    Args:
        first_name: Teacher first name
        last_name: Teacher last name
        school_name: School name
        doc_type: Document type: "id_card", "hr_system", "payslip", "verification_letter", "offer_letter", "blank"
        shared_data: Optional pre-created TeacherDocumentData for sync
        school_template: Optional school template folder: "kinkaid_school", "springfield_high", "thomas_jefferson"
        
    Returns:
        PNG image bytes
    """
    if doc_type == "blank":
        return generate_blank_image()
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright required, run `pip install playwright` then `playwright install chromium`"
        ) from exc

    # Create or use shared data for synchronization
    if shared_data is None:
        shared_data = TeacherDocumentData(first_name, last_name, school_name)

    # Use default school template if not specified
    school = school_template or DEFAULT_SCHOOL_TEMPLATE

    # Select template based on type
    if doc_type == "hr_system":
        html = _render_hr_template(shared_data, school)
        selector = ".browser-mockup"
        viewport = {"width": 1200, "height": 1000}
    elif doc_type == "payslip":
        html = _render_payslip_template(shared_data, school)
        selector = ".payslip-container"
        viewport = {"width": 800, "height": 600}
    elif doc_type == "verification_letter":
        html = _render_verification_letter_template(shared_data, school)
        selector = "body"
        viewport = {"width": 850, "height": 1100}
    elif doc_type == "offer_letter":
        html = _render_offer_letter_template(shared_data, school)
        selector = "body"
        viewport = {"width": 850, "height": 1100}
    else:  # id_card (default)
        html = _render_id_card_template(shared_data, school)
        selector = ".id-card"
        viewport = {"width": 500, "height": 400}

    print(f"DEBUG: Generating {doc_type} PNG...")
    try:
        with sync_playwright() as p:
            print("DEBUG: Launching browser...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=viewport)
            
            print("DEBUG: Setting content...")
            # Set timeout to avoidance infinite hang (15s)
            page.set_content(html, wait_until="load", timeout=15000)
            
            # Reduce wait time or remove if networkidle is used, but 200ms is safe for rendering
            page.wait_for_timeout(200)
            
            print("DEBUG: Taking screenshot...")
            element = page.locator(selector)
            png_bytes = element.screenshot(type="png", timeout=10000)
            
            browser.close()
            print("DEBUG: Generation complete.")
            
    except Exception as e:
        print(f"ERROR in generator: {e}")
        raise
    
    # Camera effects disabled - makes text hard to read
    # print("DEBUG: Applying camera effects...")
    # png_bytes = _add_camera_effects(png_bytes)
    # print("DEBUG: Camera effects applied.")
    
    return png_bytes


def generate_teacher_pdf(first_name: str, last_name: str, school_name: str = None,
                         doc_type: DocumentType = "hr_system",
                         shared_data: TeacherDocumentData = None) -> bytes:
    """Generate teacher document as PDF."""
    # Create or use shared data
    if shared_data is None:
        shared_data = TeacherDocumentData(first_name, last_name, school_name)
    
    if doc_type == "hr_system":
        html = _render_hr_template(shared_data)
    elif doc_type == "payslip":
        html = _render_payslip_template(shared_data)
    else:
        html = _render_id_card_template(shared_data)

    output = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=output, encoding="utf-8")
    if pisa_status.err:
        raise Exception("PDF generation failed")

    pdf_data = output.getvalue()
    output.close()
    return pdf_data


def create_synced_documents(first_name: str, last_name: str, school_name: str = None) -> dict:
    """
    Generate all document types with synchronized data.
    
    Returns dict with PNG bytes for each type:
    - id_card
    - hr_system
    - payslip
    
    All documents share the SAME Employee ID and school info.
    """
    # Create shared data ONCE
    shared_data = TeacherDocumentData(first_name, last_name, school_name)
    
    result = {
        "shared_data": {
            "employee_id": shared_data.employee_id,
            "employee_id_formatted": shared_data.employee_id_formatted,
            "school_name": shared_data.school_name,
            "district_name": shared_data.district_name,
            "full_name": shared_data.full_name,
        },
        "documents": {}
    }
    
    # Generate all documents with SAME shared data
    for doc_type in ["id_card", "hr_system", "payslip"]:
        result["documents"][doc_type] = generate_teacher_png(
            first_name, last_name, school_name, 
            doc_type=doc_type, 
            shared_data=shared_data
        )
    
    return result


# Legacy alias
def generate_teacher_image(first_name: str, last_name: str, school_name: str = None) -> bytes:
    return generate_teacher_png(first_name, last_name, school_name, doc_type="id_card")


# ============================================================================
# SAVE TO SCHOOL FOLDER FUNCTION
# ============================================================================

def generate_and_save_all_documents(first_name: str, last_name: str, 
                                     school_template: SchoolTemplate = None) -> dict:
    """
    Generate and save all documents to school-specific output folder.
    
    Args:
        first_name: Teacher first name
        last_name: Teacher last name  
        school_template: Optional school template, random if not specified
        
    Returns:
        dict with file paths and shared data info
    """
    # Create shared data
    shared_data = TeacherDocumentData(first_name, last_name, school_template=school_template)
    school = shared_data.school_template
    
    # Create output folder path
    output_dir = Path(__file__).parent / "output" / school
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        "school_template": school,
        "output_folder": str(output_dir),
        "shared_data": {
            "full_name": shared_data.full_name,
            "employee_id": shared_data.employee_id_formatted,
            "salary": shared_data.salary_formatted,
            "school_name": shared_data.school_name,
            "district": shared_data.district_name,
        },
        "files": {}
    }
    
    # Document types to generate (for SheerID upload)
    doc_types = ["id_card", "payslip", "offer_letter"]
    
    for doc_type in doc_types:
        # Generate document
        png_bytes = generate_teacher_png(
            first_name, last_name, 
            doc_type=doc_type,
            shared_data=shared_data
        )
        
        # Save to school folder with document name
        filename = f"{doc_type}.png"
        filepath = output_dir / filename
        filepath.write_bytes(png_bytes)
        
        result["files"][doc_type] = str(filepath)
    
    return result

