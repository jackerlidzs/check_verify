"""Penn State LionPATH Template - Exact Match to Reference"""


def get_lionpath_html_template(name, psu_id, email, major, date, course_rows):
    """Return the LionPATH HTML template with data filled in - matches reference exactly"""
    # Parse first name for Welcome message
    first_name = name.split()[0] if ' ' in name else name
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Roboto', Arial, sans-serif;
            background: #e8e8e8;
            color: #333;
            font-size: 14px;
            line-height: 1.4;
        }}
        
        .container {{
            width: 816px;
            background: white;
            margin: 0 auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: #1e407c;
            color: white;
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .psu-logo {{
            font-size: 22px;
            font-weight: bold;
            font-style: italic;
            color: white;
        }}
        
        .separator {{
            color: #7a9fd4;
            font-weight: 300;
        }}
        
        .system-name {{
            font-size: 16px;
            font-weight: 400;
            color: #c5d4eb;
        }}
        
        .header-right {{
            font-size: 13px;
        }}
        
        .header-right a {{
            color: white;
            margin-left: 15px;
            text-decoration: none;
        }}
        
        .nav-bar {{
            background: #f5f5f5;
            padding: 0 25px;
            display: flex;
            gap: 25px;
            border-bottom: 1px solid #ddd;
        }}
        
        .nav-item {{
            color: #333;
            font-size: 13px;
            padding: 12px 0;
            cursor: pointer;
        }}
        
        .nav-item.active {{
            color: #1e407c;
            font-weight: 500;
            border-bottom: 3px solid #1e407c;
        }}
        
        .content {{
            padding: 30px 25px;
            background: white;
        }}
        
        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }}
        
        .page-title {{
            font-size: 24px;
            font-weight: 400;
            color: #1e407c;
        }}
        
        .term-button {{
            background: white;
            border: 1px solid #999;
            padding: 6px 12px;
            font-size: 13px;
            font-family: inherit;
            cursor: pointer;
        }}
        
        .student-info {{
            display: flex;
            border: 1px solid #ddd;
            margin-bottom: 20px;
        }}
        
        .info-group {{
            padding: 15px 20px;
            border-right: 1px solid #ddd;
        }}
        
        .info-group:last-child {{
            border-right: none;
        }}
        
        .info-label {{
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .info-value {{
            font-size: 14px;
            font-weight: 500;
        }}
        
        .enrolled-badge {{
            background: #d4edda;
            color: #155724;
            padding: 8px 15px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .enrolled-badge::before {{
            content: "✓";
            font-weight: bold;
        }}
        
        .data-timestamp {{
            text-align: right;
            font-size: 11px;
            color: #666;
            margin-bottom: 15px;
        }}
        
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        
        .schedule-table th {{
            background: white;
            color: #333;
            padding: 15px 8px;
            text-align: left;
            font-size: 13px;
            font-weight: 500;
            border-bottom: 2px solid #1e407c;
        }}
        
        .schedule-table th:nth-child(1) {{ width: 70px; }}
        .schedule-table th:nth-child(2) {{ width: 90px; }}
        .schedule-table th:nth-child(3) {{ width: 200px; }}
        .schedule-table th:nth-child(4) {{ width: 160px; }}
        .schedule-table th:nth-child(5) {{ width: 100px; }}
        .schedule-table th:nth-child(6) {{ width: 50px; }}
        
        .schedule-table td {{
            padding: 18px 8px;
            border-bottom: 1px solid #eaeaea;
            font-size: 13px;
            vertical-align: top;
        }}
        
        .schedule-table tbody tr:hover {{
            background: #fafafa;
        }}
        
        .course-code {{
            font-weight: 500;
            color: #1e407c;
            text-decoration: underline;
        }}
        
        .footer {{
            margin-top: 50px;
            padding: 20px;
            background: #f5f5f5;
            text-align: center;
            font-size: 11px;
            color: #666;
        }}
        
        .footer-text {{
            margin-bottom: 3px;
        }}
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div class="header-left">
            <span class="psu-logo">PennState</span>
            <span class="separator">|</span>
            <span class="system-name">LionPATH</span>
        </div>
        <div class="header-right">
            Welcome, <strong>{name}</strong> <span class="separator">|</span> <a href="#">Sign Out</a>
        </div>
    </div>
    
    <div class="nav-bar">
        <span class="nav-item">Student Home</span>
        <span class="nav-item active">My Class Schedule</span>
        <span class="nav-item">Academics</span>
        <span class="nav-item">Finances</span>
        <span class="nav-item">Campus Life</span>
    </div>
    
    <div class="content">
        <div class="page-header">
            <div class="page-title">My Class Schedule</div>
            <button class="term-button">Term: Spring 2026 (Jan 12 - May 1)</button>
        </div>
        
        <div class="student-info">
            <div class="info-group">
                <div class="info-label">Student Name</div>
                <div class="info-value">{name}</div>
            </div>
            <div class="info-group">
                <div class="info-label">PSU ID</div>
                <div class="info-value">{psu_id}</div>
            </div>
            <div class="info-group">
                <div class="info-label">Academic Program</div>
                <div class="info-value">{major}</div>
            </div>
            <div class="info-group">
                <div class="info-label">Enrollment Status</div>
                <div class="enrolled-badge">Enrolled</div>
            </div>
        </div>
        
        <div class="data-timestamp">Data retrieved: {date}</div>
        
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Class Nbr</th>
                    <th>Course</th>
                    <th>Title</th>
                    <th>Days & Times</th>
                    <th>Room</th>
                    <th>Units</th>
                </tr>
            </thead>
            <tbody>
                {course_rows}
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <div class="footer-text">© 2026 The Pennsylvania State University. All rights reserved.</div>
        <div class="footer-text">LionPATH is the student information system for Penn State.</div>
    </div>
</div>

</body>
</html>"""
