"""
Teacher Badge Generator

Creates professional-looking teacher ID badge documents for SheerID verification.
Uses HTML/CSS template converted to PNG image.
"""
import os
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Try to import playwright for screenshot
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def generate_employee_id() -> str:
    """Generate random employee ID."""
    prefix = random.choice(['EMP', 'TCH', 'EDU', 'FAC'])
    numbers = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{numbers}"


def get_academic_year() -> str:
    """Get current academic year string."""
    now = datetime.now()
    if now.month >= 8:  # Aug-Dec = Fall semester
        return f"{now.year}-{now.year + 1}"
    else:  # Jan-Jul = Spring semester
        return f"{now.year - 1}-{now.year}"


def generate_badge_html(teacher_data: Dict, school: Dict) -> str:
    """
    Generate HTML for teacher ID badge.
    
    Args:
        teacher_data: Dict with first_name, last_name, email, etc.
        school: Dict with name, district, etc.
    
    Returns:
        HTML string for badge
    """
    first_name = teacher_data.get('first_name', 'John')
    last_name = teacher_data.get('last_name', 'Doe')
    full_name = f"{first_name} {last_name}"
    email = teacher_data.get('email', 'teacher@school.edu')
    position = teacher_data.get('position', 'Teacher')
    department = teacher_data.get('department', 'Education')
    
    school_name = school.get('name', 'Public High School')
    district = school.get('district', 'School District')
    
    employee_id = generate_employee_id()
    academic_year = get_academic_year()
    issue_date = datetime.now().strftime("%m/%d/%Y")
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f0f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .badge {{
            width: 400px;
            background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #1a365d 100%);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        .header {{
            background: #fff;
            padding: 16px 20px;
            text-align: center;
            border-bottom: 4px solid #c53030;
        }}
        .school-name {{
            font-size: 18px;
            font-weight: 700;
            color: #1a365d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .district {{
            font-size: 11px;
            color: #666;
            margin-top: 4px;
        }}
        .content {{
            padding: 24px;
            color: white;
        }}
        .photo-section {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .photo {{
            width: 100px;
            height: 120px;
            background: #e2e8f0;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #718096;
            font-size: 12px;
        }}
        .info {{
            flex: 1;
        }}
        .name {{
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #fff;
        }}
        .position {{
            font-size: 14px;
            color: #bee3f8;
            margin-bottom: 4px;
        }}
        .department {{
            font-size: 12px;
            color: #90cdf4;
        }}
        .details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}
        .detail-item {{
            font-size: 11px;
        }}
        .detail-label {{
            color: #90cdf4;
            text-transform: uppercase;
            font-size: 9px;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }}
        .detail-value {{
            color: #fff;
            font-weight: 500;
        }}
        .footer {{
            background: #c53030;
            padding: 12px 20px;
            text-align: center;
        }}
        .academic-year {{
            font-size: 14px;
            font-weight: 600;
            color: #fff;
        }}
        .valid {{
            font-size: 10px;
            color: rgba(255,255,255,0.8);
            margin-top: 2px;
        }}
    </style>
</head>
<body>
    <div class="badge">
        <div class="header">
            <div class="school-name">{school_name}</div>
            <div class="district">{district}</div>
        </div>
        <div class="content">
            <div class="photo-section">
                <div class="photo">PHOTO</div>
                <div class="info">
                    <div class="name">{full_name}</div>
                    <div class="position">{position}</div>
                    <div class="department">{department}</div>
                </div>
            </div>
            <div class="details">
                <div class="detail-item">
                    <div class="detail-label">Employee ID</div>
                    <div class="detail-value">{employee_id}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Issue Date</div>
                    <div class="detail-value">{issue_date}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Email</div>
                    <div class="detail-value" style="font-size: 10px;">{email}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">Active</div>
                </div>
            </div>
        </div>
        <div class="footer">
            <div class="academic-year">Academic Year {academic_year}</div>
            <div class="valid">This ID is property of {school_name}</div>
        </div>
    </div>
</body>
</html>'''
    return html


def generate_badge_image(teacher_data: Dict, school: Dict, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Generate teacher badge as PNG image using Playwright.
    
    Args:
        teacher_data: Dict with teacher info
        school: Dict with school info
        output_path: Optional path for output file
    
    Returns:
        Path to generated image, or None if failed
    """
    if not HAS_PLAYWRIGHT:
        return None
    
    # Generate HTML
    html = generate_badge_html(teacher_data, school)
    
    # Default output path
    if output_path is None:
        output_dir = Path(__file__).parent / "generated"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"teacher_badge_{timestamp}.png"
    
    # Create temp HTML file
    temp_html = Path(__file__).parent / "temp_badge.html"
    temp_html.write_text(html, encoding='utf-8')
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 500, 'height': 600})
            page.goto(f'file:///{temp_html.absolute()}')
            page.wait_for_timeout(500)  # Wait for render
            
            # Screenshot the badge element
            badge = page.locator('.badge')
            badge.screenshot(path=str(output_path))
            
            browser.close()
        
        # Cleanup temp file
        temp_html.unlink()
        
        return output_path
    except Exception as e:
        print(f"Badge generation error: {e}")
        if temp_html.exists():
            temp_html.unlink()
        return None


def generate_simple_badge(teacher_data: Dict, school: Dict, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Generate a simple badge using PIL (fallback if Playwright fails).
    
    Creates a basic text-based badge image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    
    # Create image
    width, height = 400, 250
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 16)
        font_name = ImageFont.truetype("arialbd.ttf", 20)
        font_text = ImageFont.truetype("arial.ttf", 12)
    except:
        font_title = ImageFont.load_default()
        font_name = font_title
        font_text = font_title
    
    # School header
    school_name = school.get('name', 'Public School')
    draw.rectangle([0, 0, width, 50], fill='#1a365d')
    draw.text((width//2, 25), school_name, fill='white', anchor='mm', font=font_title)
    
    # Teacher info
    full_name = f"{teacher_data.get('first_name', 'John')} {teacher_data.get('last_name', 'Doe')}"
    draw.text((width//2, 90), full_name, fill='#1a365d', anchor='mm', font=font_name)
    draw.text((width//2, 120), teacher_data.get('position', 'Teacher'), fill='#666', anchor='mm', font=font_text)
    
    # Details
    employee_id = generate_employee_id()
    issue_date = datetime.now().strftime("%m/%d/%Y")
    academic_year = get_academic_year()
    
    draw.text((50, 150), f"Employee ID: {employee_id}", fill='#333', font=font_text)
    draw.text((50, 170), f"Issue Date: {issue_date}", fill='#333', font=font_text)
    draw.text((50, 190), f"Email: {teacher_data.get('email', 'N/A')}", fill='#333', font=font_text)
    
    # Footer
    draw.rectangle([0, height-30, width, height], fill='#c53030')
    draw.text((width//2, height-15), f"Academic Year {academic_year}", fill='white', anchor='mm', font=font_text)
    
    # Save
    if output_path is None:
        output_dir = Path(__file__).parent / "generated"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"teacher_badge_{timestamp}.png"
    
    img.save(output_path)
    return output_path


def create_teacher_badge(teacher_data: Dict, school: Dict, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Create teacher badge - tries Playwright first, falls back to PIL.
    
    Args:
        teacher_data: Dict with first_name, last_name, email, position, department
        school: Dict with name, district
        output_path: Optional output path
    
    Returns:
        Path to generated badge image, or None if all methods fail
    """
    # Try Playwright first (better quality)
    result = generate_badge_image(teacher_data, school, output_path)
    if result:
        return result
    
    # Fallback to PIL
    result = generate_simple_badge(teacher_data, school, output_path)
    if result:
        return result
    
    return None


# Test
if __name__ == "__main__":
    test_teacher = {
        'first_name': 'Sarah',
        'last_name': 'Johnson',
        'email': 'sjohnson@school.edu',
        'position': 'Mathematics Teacher',
        'department': 'Mathematics'
    }
    test_school = {
        'name': 'Lincoln High School',
        'district': 'Los Angeles Unified School District'
    }
    
    path = create_teacher_badge(test_teacher, test_school)
    if path:
        print(f"Badge created: {path}")
    else:
        print("Failed to create badge")
