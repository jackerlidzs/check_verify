"""Penn State Offer of Admission Letter Template"""
import random
import base64
import os
from datetime import datetime


def generate_offer_letter_html(first_name, last_name, psu_id_func, generate_email_func):
    """
    Generate Penn State Offer of Admission Details HTML
    
    Based on official Penn State admission letter format.
    """
    # Majors and Colleges mapping
    college_majors = [
        {'college': 'College of Engineering', 'major': 'Computer Engineering'},
        {'college': 'College of Engineering', 'major': 'Electrical Engineering'},
        {'college': 'College of Engineering', 'major': 'Mechanical Engineering'},
        {'college': 'College of Engineering', 'major': 'Software Engineering'},
        {'college': 'College of Information Sciences and Technology', 'major': 'Information Sciences and Technology'},
        {'college': 'College of Information Sciences and Technology', 'major': 'Data Sciences'},
        {'college': 'Smeal College of Business', 'major': 'Finance'},
        {'college': 'Smeal College of Business', 'major': 'Marketing'},
        {'college': 'College of Liberal Arts', 'major': 'Psychology'},
    ]
    
    # PA cities for addresses
    pa_cities = [
        {'city': 'Pittsburgh', 'zip': '15201'},
        {'city': 'Philadelphia', 'zip': '19103'},
        {'city': 'Harrisburg', 'zip': '17101'},
        {'city': 'Allentown', 'zip': '18101'},
        {'city': 'Erie', 'zip': '16501'},
        {'city': 'Reading', 'zip': '19601'},
        {'city': 'State College', 'zip': '16801'},
        {'city': 'Bethlehem', 'zip': '18015'},
    ]
    
    # Street names
    streets = ['Oak St', 'Maple Ave', 'Main St', 'Cedar Ln', 'Pine Dr', 'Elm St', 'Washington Ave', 'Park Blvd']
    
    name = f"{first_name} {last_name}"
    psu_id = psu_id_func()
    selected = random.choice(college_majors)
    college = selected['college']
    major = selected['major']
    city_info = random.choice(pa_cities)
    street = f"{random.randint(100, 9999)} {random.choice(streets)}"
    
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    
    # Load Penn State logo as base64
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'psu_logo.png')
    try:
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
        logo_img = f'<img src="data:image/png;base64,{logo_base64}" alt="Penn State" style="height: 55px;">'
    except FileNotFoundError:
        logo_img = '<div style="font-size: 24pt; font-weight: bold; color: #041E42;">PennState</div>'
    
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
            font-size: 11pt;
            line-height: 1.5;
        }}
        
        .letter-container {{
            width: 8.5in;
            min-height: 11in;
            padding: 0.75in 1in;
            background: white;
        }}
        
        .header {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 25px;
        }}
        
        .header-left {{
            flex: 1;
        }}
        
        .header-center {{
            flex: 1.5;
            text-align: left;
            font-size: 10pt;
            padding-left: 20px;
        }}
        
        .header-center .dept {{
            font-weight: bold;
            color: #041E42;
            margin-bottom: 5px;
        }}
        
        .header-right {{
            flex: 1;
            text-align: right;
            font-size: 9pt;
            color: #333;
        }}
        
        .date-section {{
            display: flex;
            margin: 30px 0 20px 0;
        }}
        
        .date {{
            flex: 1;
        }}
        
        .offer-details {{
            flex: 1.5;
        }}
        
        .offer-details-title {{
            font-weight: bold;
            color: #041E42;
            margin-bottom: 10px;
            font-size: 12pt;
        }}
        
        .offer-details table {{
            font-size: 10pt;
        }}
        
        .offer-details td {{
            padding: 2px 0;
        }}
        
        .offer-details td:first-child {{
            padding-right: 10px;
        }}
        
        .offer-details td:last-child {{
            font-weight: bold;
        }}
        
        .student-address {{
            margin: 30px 0 25px 0;
            line-height: 1.4;
        }}
        
        .salutation {{
            margin-bottom: 20px;
        }}
        
        .body-text {{
            text-align: justify;
            margin-bottom: 15px;
        }}
        
        .signature {{
            margin-top: 30px;
        }}
        
        .signature-name {{
            margin-top: 40px;
            font-weight: bold;
        }}
        
        .signature-title {{
            font-size: 10pt;
        }}
        
        .ps-note {{
            margin-top: 30px;
            font-size: 10pt;
        }}
        
        .footer {{
            position: absolute;
            bottom: 0.5in;
            left: 1in;
            right: 1in;
            font-size: 8pt;
            color: #666;
            text-align: right;
            font-style: italic;
        }}
    </style>
</head>
<body>

<div class="letter-container">
    <div class="header">
        <div class="header-left">
            {logo_img}
        </div>
        <div class="header-center">
            <div class="dept">Undergraduate Admissions Office</div>
            The Pennsylvania State University<br>
            201 Shields Building<br>
            University Park, PA 16802-1294
        </div>
        <div class="header-right">
            Phone: 814-865-5471<br>
            Fax: 814-863-7590<br>
            Website: admissions.psu.edu<br>
            Email: admissions@psu.edu
        </div>
    </div>
    
    <div class="date-section">
        <div class="date">{date_str}</div>
        <div class="offer-details">
            <div class="offer-details-title">Offer of Admission Details</div>
            <table>
                <tr>
                    <td>Penn State ID:</td>
                    <td>{psu_id}</td>
                </tr>
                <tr>
                    <td>Campus:</td>
                    <td>University Park</td>
                </tr>
                <tr>
                    <td>Term:</td>
                    <td>Spring 2026</td>
                </tr>
                <tr>
                    <td>College:</td>
                    <td>{college}</td>
                </tr>
                <tr>
                    <td>Intended Major:</td>
                    <td>{major}</td>
                </tr>
                <tr>
                    <td>Residency:</td>
                    <td>Resident (In State)</td>
                </tr>
            </table>
        </div>
    </div>
    
    <div class="student-address">
        {name}<br>
        {street}<br>
        {city_info['city']}, PA {city_info['zip']}
    </div>
    
    <div class="salutation">Dear {first_name},</div>
    
    <div class="body-text">
        <strong>Congratulations! You have been admitted to Penn State!</strong>
    </div>
    
    <div class="body-text">
        You did it. Your hard work has paid off and it's time to look ahead to what's next. By choosing Penn State, you 
        not only gain the support of a globally recognized university with the resources of twenty campuses located 
        throughout the state, you join a community rooted in supporting and inspiring one another. This community will 
        be with you for life. You will benefit from an academic community that will connect you to the expertise, 
        research, and resources you need to accomplish your life and career goals.
    </div>
    
    <div class="body-text">
        I am so pleased to offer you admission to the {college} with the intended major of {major} 
        for Spring 2026 at Penn State University Park. We are excited to welcome you to the Penn State family!
    </div>
    
    <div class="body-text">
        In the <em>New Student Guide</em>, available in MyPennState, you will find instructions for accepting our offer, the 
        conditions of our offer, contact information for offices across the University, and a description of what will 
        occur between the time you accept our offer and your first day of classes.
    </div>
    
    <div class="body-text">
        As you consider your college options, I encourage you to learn more about what Penn State can offer 
        you by visiting <strong>admissions.psu.edu/accepted</strong>.
    </div>
    
    <div class="body-text">
        Congratulations, and welcome to Penn State!
    </div>
    
    <div class="signature">
        Sincerely,
        
        <div class="signature-name">Robert G. Springall</div>
        <div class="signature-title">Executive Director of Undergraduate Admissions</div>
    </div>
    
    <div class="ps-note">
        P.S. Your PSU ID number is {psu_id}. Please use this on all correspondence with Penn State.
    </div>
    
    <div class="footer">
        An Equal Opportunity University
    </div>
</div>

</body>
</html>
"""
    return html
