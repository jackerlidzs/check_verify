"""PNG 学生证生成模块 - Penn State LionPATH"""
import random
from datetime import datetime
from io import BytesIO
import base64

# Real Penn State courses from bulletins.psu.edu
COURSE_POOL = [
    # CMPSC Core Courses
    {"code": "CMPSC 101", "title": "Introduction to Programming", "credits": 3},
    {"code": "CMPSC 121", "title": "Introduction to Programming", "credits": 3},
    {"code": "CMPSC 122", "title": "Intermediate Programming", "credits": 3},
    {"code": "CMPSC 131", "title": "Programming and Computation I", "credits": 3},
    {"code": "CMPSC 132", "title": "Programming and Computation II", "credits": 3},
    {"code": "CMPSC 221", "title": "Object-Oriented Programming with Web", "credits": 3},
    {"code": "CMPSC 311", "title": "Introduction to Systems Programming", "credits": 3},
    {"code": "CMPSC 360", "title": "Discrete Mathematics for Computer Science", "credits": 3},
    {"code": "CMPSC 421", "title": "Net-centric Computing", "credits": 3},
    {"code": "CMPSC 431W", "title": "Database Management Systems", "credits": 3},
    {"code": "CMPSC 442", "title": "Artificial Intelligence", "credits": 3},
    {"code": "CMPSC 448", "title": "Machine Learning and AI", "credits": 3},
    {"code": "CMPSC 461", "title": "Programming Language Concepts", "credits": 3},
    {"code": "CMPSC 462", "title": "Data Structures", "credits": 3},
    {"code": "CMPSC 464", "title": "Introduction to Theory of Computation", "credits": 3},
    {"code": "CMPSC 465", "title": "Data Structures and Algorithms", "credits": 3},
    {"code": "CMPSC 473", "title": "Operating Systems Design", "credits": 3},
    {"code": "CMPSC 474", "title": "Compiler Design", "credits": 3},
    {"code": "CMPSC 483W", "title": "Software Engineering Design", "credits": 3},
    # Math/Science Support Courses
    {"code": "MATH 140", "title": "Calculus with Analytic Geometry I", "credits": 4},
    {"code": "MATH 141", "title": "Calculus with Analytic Geometry II", "credits": 4},
    {"code": "MATH 220", "title": "Matrices", "credits": 2},
    {"code": "MATH 230", "title": "Calculus and Vector Analysis", "credits": 4},
    {"code": "STAT 318", "title": "Elementary Probability", "credits": 3},
    {"code": "PHYS 211", "title": "General Physics: Mechanics", "credits": 4},
    {"code": "ENGL 202C", "title": "Technical Writing", "credits": 3},
    {"code": "CYBER 262", "title": "Introduction to Cybersecurity", "credits": 3},
]

# Real Penn State buildings and room numbers
ROOM_POOL = [
    "Willard 062", "Willard 101", "Willard 143", "Willard 210",
    "Thomas 102", "Thomas 201", "Thomas 305",
    "Westgate E101", "Westgate E201", "Westgate E302",
    "Boucke 101", "Boucke 207", "Boucke 304",
    "Osmond 101", "Osmond 112", "Osmond 215",
    "IST 110", "IST 220", "IST 315",
    "Hammond 101", "Hammond 203", "Hammond 312",
    "Sackett 105", "Sackett 211", "Sackett 323",
]

# Realistic Penn State time slots
TIME_SLOTS = [
    "MoWeFr 8:00AM - 8:50AM",
    "MoWeFr 9:05AM - 9:55AM",
    "MoWeFr 10:10AM - 11:00AM",
    "MoWeFr 11:15AM - 12:05PM",
    "MoWeFr 1:25PM - 2:15PM",
    "MoWeFr 2:30PM - 3:20PM",
    "TuTh 8:00AM - 9:15AM",
    "TuTh 9:45AM - 11:00AM",
    "TuTh 11:15AM - 12:30PM",
    "TuTh 1:35PM - 2:50PM",
    "TuTh 3:05PM - 4:20PM",
    "MoWe 2:30PM - 3:45PM",
    "MoWe 4:00PM - 5:15PM",
]

# Realistic instructor names (last name only - matches LionPATH format)
INSTRUCTOR_POOL = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Anderson", "Taylor", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Robinson", "Clark",
    "Lewis", "Lee", "Walker", "Hall", "Allen",
    "Young", "King", "Wright", "Scott", "Green",
]


def generate_random_schedule(num_courses=None):
    """Generate random course schedule with 4-6 courses"""
    if num_courses is None:
        num_courses = random.randint(4, 6)
    
    # Select random courses without duplicates
    courses = random.sample(COURSE_POOL, min(num_courses, len(COURSE_POOL)))
    
    # Assign random rooms, times, and instructors (no duplicates)
    rooms = random.sample(ROOM_POOL, num_courses)
    times = random.sample(TIME_SLOTS, num_courses)
    instructors = random.sample(INSTRUCTOR_POOL, num_courses)
    
    schedule = []
    for i, course in enumerate(courses):
        schedule.append({
            "class_nbr": str(random.randint(10000, 29999)),
            "code": course["code"],
            "title": course["title"],
            "time": times[i],
            "room": rooms[i],
            "credits": f"{course['credits']:.2f}",
            "instructor": instructors[i],
        })
    
    return schedule


def generate_psu_id():
    """生成随机 PSU ID (9位数字)"""
    return f"9{random.randint(10000000, 99999999)}"


def generate_psu_email(first_name, last_name):
    """
    Generate PSU email in official Penn State format
    Format: {first_initial}{middle_initial}{last_initial}{3-4 digits}@psu.edu
    Example: hkb5474@psu.edu
    """
    # Get initials (lowercase)
    first_init = first_name[0].lower()
    last_init = last_name[0].lower()
    
    # Generate random middle initial (exclude vowels for realism)
    consonants = 'bcdfghjklmnpqrstvwxyz'
    mid_init = random.choice(consonants)
    
    # Generate 3-4 digit number
    num_digits = random.choice([3, 4])
    number = random.randint(10**(num_digits-1), 10**num_digits - 1)
    
    user_id = f"{first_init}{mid_init}{last_init}{number}"
    return f"{user_id}@psu.edu"


def generate_html(first_name, last_name, school_id='2565'):
    """
    生成 Penn State LionPATH HTML

    Args:
        first_name: 名字
        last_name: 姓氏
        school_id: 学校 ID

    Returns:
        str: HTML 内容
    """
    psu_id = generate_psu_id()
    name = f"{first_name} {last_name}"
    date = datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')

    # 随机选择专业
    majors = [
        'Computer Science (BS)',
        'Software Engineering (BS)',
        'Information Sciences and Technology (BS)',
        'Data Science (BS)',
        'Electrical Engineering (BS)',
        'Mechanical Engineering (BS)',
        'Business Administration (BS)',
        'Psychology (BA)'
    ]
    major = random.choice(majors)

    # Generate random course schedule
    schedule = generate_random_schedule()
    course_rows = ""
    for course in schedule:
        course_rows += f"""
                <tr>
                    <td>{course['class_nbr']}</td>
                    <td class="course-code">{course['code']}</td>
                    <td class="course-title">{course['title']}</td>
                    <td>{course['instructor']}</td>
                    <td>{course['time']}</td>
                    <td>{course['room']}</td>
                    <td>{course['credits']}</td>
                </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LionPATH - Student Home</title>
    <style>
        :root {{
            --psu-blue: #1E407C; /* Penn State Nittany Navy */
            --psu-light-blue: #96BEE6;
            --bg-gray: #f4f4f4;
            --text-color: #333;
        }}

        body {{
            font-family: "Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background-color: #e0e0e0; /* 浏览器背景 */
            margin: 0;
            padding: 20px;
            color: var(--text-color);
            display: flex;
            justify-content: center;
        }}

        /* 模拟浏览器窗口 */
        .viewport {{
            width: 100%;
            max-width: 1100px;
            background-color: #fff;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            min-height: 800px;
            display: flex;
            flex-direction: column;
        }}

        /* 顶部导航栏 LionPATH */
        .header {{
            background-color: var(--psu-blue);
            color: white;
            padding: 0 20px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        /* PSU Logo 模拟 */
        .psu-logo {{
            font-family: "Georgia", serif;
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 1px;
            border-right: 1px solid rgba(255,255,255,0.3);
            padding-right: 15px;
        }}

        .system-name {{
            font-size: 18px;
            font-weight: 300;
        }}

        .user-menu {{
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .nav-bar {{
            background-color: #f8f8f8;
            border-bottom: 1px solid #ddd;
            padding: 10px 20px;
            font-size: 13px;
            color: #666;
            display: flex;
            gap: 20px;
        }}
        .nav-item {{ cursor: pointer; }}
        .nav-item.active {{ color: var(--psu-blue); font-weight: bold; border-bottom: 2px solid var(--psu-blue); padding-bottom: 8px; }}

        /* 主内容区 */
        .content {{
            padding: 30px;
            flex: 1;
        }}

        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 20px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}

        .page-title {{
            font-size: 24px;
            color: var(--psu-blue);
            margin: 0;
        }}

        .term-selector {{
            background: #fff;
            border: 1px solid #ccc;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 14px;
            color: #333;
            font-weight: bold;
        }}

        /* 学生信息卡片 */
        .student-card {{
            background: #fcfcfc;
            border: 1px solid #e0e0e0;
            padding: 15px;
            margin-bottom: 25px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            font-size: 13px;
        }}
        .info-label {{ color: #777; font-size: 11px; text-transform: uppercase; margin-bottom: 4px; }}
        .info-val {{ font-weight: bold; color: #333; font-size: 14px; }}
        .status-badge {{
            background-color: #e6fffa; color: #007a5e;
            padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #b2f5ea;
        }}

        /* 课程表 */
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .schedule-table th {{
            text-align: left;
            padding: 12px;
            background-color: #f0f0f0;
            border-bottom: 2px solid #ccc;
            color: #555;
        }}

        .schedule-table td {{
            padding: 15px 12px;
            border-bottom: 1px solid #eee;
        }}

        .course-code {{ font-weight: bold; color: var(--psu-blue); }}
        .course-title {{ font-weight: 500; }}

        /* 打印适配 */
        @media print {{
            body {{ background: white; padding: 0; }}
            .viewport {{ box-shadow: none; max-width: 100%; min-height: auto; }}
            .nav-bar {{ display: none; }}
            @page {{ margin: 1cm; size: landscape; }}
        }}
    </style>
</head>
<body>

<div class="viewport">
    <div class="header">
        <div class="brand">
            <div class="psu-logo">The Pennsylvania State University</div>
            <div class="system-name">LionPATH Student Information System</div>
        </div>
        <div class="user-menu">
            <span>Welcome, <strong>{name}</strong></span>
            <span>|</span>
            <span>Sign Out</span>
        </div>
    </div>

    <div class="nav-bar">
        <div class="nav-item">Student Home</div>
        <div class="nav-item active">My Class Schedule</div>
        <div class="nav-item">Academics</div>
        <div class="nav-item">Finances</div>
        <div class="nav-item">Campus Life</div>
    </div>

    <div class="content">
        <div class="page-header">
            <h1 class="page-title">My Class Schedule</h1>
            <div class="term-selector" style="background: #e8f4e8; padding: 8px 15px; border-radius: 5px; border: 1px solid #4caf50;">
                <strong style="color: #2e7d32;">CURRENT TERM:</strong> <strong>Spring 2026</strong> (January 12, 2026 - May 1, 2026)
            </div>
        </div>

        <div class="student-card" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
            <div>
                <div class="info-label">Student Name</div>
                <div class="info-val">{name}</div>
            </div>
            <div>
                <div class="info-label">PSU ID</div>
                <div class="info-val">{psu_id}</div>
            </div>
            <div>
                <div class="info-label">Academic Year</div>
                <div class="info-val">2025-2026</div>
            </div>
            <div>
                <div class="info-label">Academic Program</div>
                <div class="info-val">{major}</div>
            </div>
            <div>
                <div class="info-label">Enrollment Date</div>
                <div class="info-val">January 12, 2026</div>
            </div>
            <div>
                <div class="info-label">Enrollment Status</div>
                <div class="status-badge">✅ Enrolled</div>
            </div>
        </div>

        <div style="margin-bottom: 10px; font-size: 12px; color: #666; text-align: right;">
            Data retrieved: <span>{date}</span>
        </div>

        <table class="schedule-table">
            <thead>
                <tr>
                    <th width="8%">Class Nbr</th>
                    <th width="12%">Course</th>
                    <th width="28%">Title</th>
                    <th width="12%">Instructor</th>
                    <th width="18%">Days & Times</th>
                    <th width="12%">Room</th>
                    <th width="10%">Units</th>
                </tr>
            </thead>
            <tbody>
                {course_rows}
            </tbody>
        </table>

        <div style="margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px; font-size: 11px; color: #888; text-align: center;">
            &copy; 2026 The Pennsylvania State University. All rights reserved.<br>
            LionPATH is the student information system for Penn State.
        </div>
    </div>
</div>

</body>
</html>
"""

    return html


def generate_enrollment_letter_html(first_name, last_name, school_id='2565'):
    """
    Generate Penn State Enrollment Verification Letter HTML
    
    This document type is often trusted more by SheerID's AI as it appears
    more official than a class schedule screenshot.
    """
    from datetime import datetime
    
    # Majors list
    majors = [
        'Computer Science (BS)',
        'Software Engineering (BS)',
        'Information Sciences and Technology (BS)',
        'Data Science (BS)',
        'Electrical Engineering (BS)',
        'Mechanical Engineering (BS)',
        'Business Administration (BS)',
        'Psychology (BA)'
    ]
    
    name = f"{first_name} {last_name}"
    psu_id = generate_psu_id()
    email = generate_psu_email(first_name, last_name)
    major = random.choice(majors)
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Times New Roman', Georgia, serif;
            background: white;
            color: #000;
            font-size: 12pt;
            line-height: 1.6;
        }}
        
        .letter-container {{
            width: 8.5in;
            min-height: 11in;
            padding: 1in;
            background: white;
        }}
        
        .header {{
            display: flex;
            align-items: center;
            border-bottom: 3px solid #041E42;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 28pt;
            font-weight: bold;
            color: #041E42;
        }}
        
        .logo span {{
            color: #1E407C;
        }}
        
        .dept-info {{
            margin-left: auto;
            text-align: right;
            font-size: 10pt;
            color: #333;
        }}
        
        .title {{
            text-align: center;
            font-size: 16pt;
            font-weight: bold;
            margin: 40px 0;
            text-decoration: underline;
            color: #041E42;
        }}
        
        .date {{
            text-align: right;
            margin-bottom: 30px;
        }}
        
        .salutation {{
            margin-bottom: 20px;
        }}
        
        .body-text {{
            text-align: justify;
            margin-bottom: 20px;
        }}
        
        .details-box {{
            background: #f8f9fa;
            border: 1px solid #ddd;
            padding: 20px;
            margin: 30px 0;
        }}
        
        .details-box table {{
            width: 100%;
        }}
        
        .details-box td {{
            padding: 8px 0;
        }}
        
        .details-box td:first-child {{
            font-weight: bold;
            width: 40%;
        }}
        
        .closing {{
            margin-top: 40px;
        }}
        
        .signature {{
            margin-top: 50px;
        }}
        
        .signature-line {{
            border-bottom: 1px solid #000;
            width: 250px;
            margin-bottom: 5px;
        }}
        
        .signature-name {{
            font-weight: bold;
        }}
        
        .footer {{
            position: absolute;
            bottom: 1in;
            left: 1in;
            right: 1in;
            font-size: 9pt;
            color: #666;
            text-align: center;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
        
        .verification-stamp {{
            position: absolute;
            top: 2in;
            right: 1.5in;
            border: 2px solid #041E42;
            color: #041E42;
            padding: 10px 20px;
            font-weight: bold;
            transform: rotate(-15deg);
            opacity: 0.8;
        }}
    </style>
</head>
<body>

<div class="letter-container">
    <div class="header">
        <div class="logo">
            Penn<span>State</span>
        </div>
        <div class="dept-info">
            <strong>Office of the Registrar</strong><br>
            112 Shields Building<br>
            University Park, PA 16802<br>
            (814) 865-6357
        </div>
    </div>
    
    <div class="verification-stamp">
        VERIFIED ✓
    </div>
    
    <div class="title">ENROLLMENT VERIFICATION LETTER</div>
    
    <div class="date">{date_str}</div>
    
    <div class="salutation">To Whom It May Concern:</div>
    
    <div class="body-text">
        This letter is to certify that <strong>{name}</strong> is currently enrolled as a 
        <strong>full-time student</strong> at The Pennsylvania State University for the 
        <strong>Spring 2026</strong> academic semester.
    </div>
    
    <div class="details-box">
        <table>
            <tr>
                <td>Student Name:</td>
                <td>{name}</td>
            </tr>
            <tr>
                <td>Penn State ID:</td>
                <td>{psu_id}</td>
            </tr>
            <tr>
                <td>Email Address:</td>
                <td>{email}</td>
            </tr>
            <tr>
                <td>Academic Program:</td>
                <td>{major}</td>
            </tr>
            <tr>
                <td>Academic Level:</td>
                <td>Undergraduate</td>
            </tr>
            <tr>
                <td>Enrollment Status:</td>
                <td>Full-Time (12+ credits)</td>
            </tr>
            <tr>
                <td>Current Term:</td>
                <td>Spring 2026 (January 12 - May 1, 2026)</td>
            </tr>
        </table>
    </div>
    
    <div class="body-text">
        This letter is issued at the request of the student for enrollment verification purposes. 
        The information above is accurate as of the date of this letter and is subject to change.
    </div>
    
    <div class="closing">
        Sincerely,
    </div>
    
    <div class="signature">
        <div class="signature-line"></div>
        <div class="signature-name">Office of the Registrar</div>
        <div>The Pennsylvania State University</div>
    </div>
    
    <div class="footer">
        The Pennsylvania State University | Office of the Registrar | registrar.psu.edu<br>
        This is an official document. For verification, contact the Office of the Registrar.
    </div>
</div>

</body>
</html>
"""
    return html


def generate_image(first_name, last_name, school_id='2565', doc_type='schedule'):
    """
    生成 Penn State 文档 PNG
    
    Args:
        first_name: 名字
        last_name: 姓氏
        school_id: 学校 ID
        doc_type: Document type - 'schedule' (default), 'enrollment_letter'

    Returns:
        bytes: PNG 图片数据
    """
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image, ImageFilter
        import numpy as np

        # Generate HTML based on document type
        if doc_type == 'enrollment_letter':
            html_content = generate_enrollment_letter_html(first_name, last_name, school_id)
        else:  # default to schedule
            html_content = generate_html(first_name, last_name, school_id)

        # 使用 Playwright 截图（替代 Selenium）
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            page.set_content(html_content, wait_until='load')
            page.wait_for_timeout(500)  # 等待样式加载
            screenshot_bytes = page.screenshot(type='png', full_page=True)
            browser.close()

        # Apply authenticity filters to bypass AI detection
        # (Makes it look more like a photo of a screen rather than a direct screenshot)
        img = Image.open(BytesIO(screenshot_bytes))
        img_array = np.array(img)
        
        # Add subtle noise (like camera sensor noise)
        noise_intensity = 3  # Very subtle
        noise = np.random.randint(-noise_intensity, noise_intensity + 1, img_array.shape, dtype=np.int16)
        noisy_img = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Convert back to PIL Image
        img = Image.fromarray(noisy_img)
        
        # Apply very slight blur (simulates camera focus)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.3))
        
        # Save back to bytes
        output = BytesIO()
        img.save(output, format='PNG', quality=95)
        return output.getvalue()

    except ImportError as e:
        # Show which module is actually missing
        missing_module = str(e)
        if 'playwright' in missing_module.lower():
            raise Exception("Playwright required: pip install playwright && playwright install chromium")
        elif 'PIL' in missing_module or 'pillow' in missing_module.lower():
            raise Exception("Pillow required: pip install Pillow")
        elif 'numpy' in missing_module.lower():
            raise Exception("NumPy required: pip install numpy")
        else:
            raise Exception(f"Import error: {missing_module}")
    except Exception as e:
        raise Exception(f"Failed to generate image: {str(e)}")


if __name__ == '__main__':
    # 测试代码
    import sys
    import io

    # 修复 Windows 控制台编码问题
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Testing PSU image generation...")

    first_name = "John"
    last_name = "Smith"

    print(f"Name: {first_name} {last_name}")
    print(f"PSU ID: {generate_psu_id()}")
    print(f"Email: {generate_psu_email(first_name, last_name)}")

    try:
        img_data = generate_image(first_name, last_name)

        # Save test image
        with open('test_psu_card.png', 'wb') as f:
            f.write(img_data)

        print(f"✓ Image generated successfully! Size: {len(img_data)} bytes")
        print("✓ Saved as test_psu_card.png")

    except Exception as e:
        print(f"✗ Error: {e}")
