"""Penn State Offer of Admission Letter Template - Exact Match"""
import random
import base64
import os
from datetime import datetime


def generate_offer_letter_html(first_name, last_name, psu_id_func, generate_email_func):
    """
    Generate Penn State Offer of Admission Details HTML
    
    Exactly matches the official Penn State admission letter format.
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
    
    # Real Pennsylvania addresses
    pa_addresses = [
        # Pittsburgh area
        {'street': '1247 Murray Ave', 'city': 'Pittsburgh', 'zip': '15217'},
        {'street': '5801 Forbes Ave', 'city': 'Pittsburgh', 'zip': '15217'},
        {'street': '412 S Highland Ave', 'city': 'Pittsburgh', 'zip': '15206'},
        # Philadelphia area
        {'street': '1520 Locust St', 'city': 'Philadelphia', 'zip': '19102'},
        {'street': '3401 Walnut St', 'city': 'Philadelphia', 'zip': '19104'},
        {'street': '2107 Chestnut St', 'city': 'Philadelphia', 'zip': '19103'},
        # Harrisburg area
        {'street': '301 Market St', 'city': 'Harrisburg', 'zip': '17101'},
        {'street': '1500 N 3rd St', 'city': 'Harrisburg', 'zip': '17102'},
        # State College (near Penn State)
        {'street': '129 S Allen St', 'city': 'State College', 'zip': '16801'},
        {'street': '411 S Burrowes St', 'city': 'State College', 'zip': '16801'},
        {'street': '720 Maple Ave', 'city': 'DuBois', 'zip': '15801'},
        # Other PA cities
        {'street': '45 N 3rd St', 'city': 'Allentown', 'zip': '18101'},
        {'street': '814 Hamilton St', 'city': 'Allentown', 'zip': '18101'},
        {'street': '300 State St', 'city': 'Erie', 'zip': '16501'},
        {'street': '1401 Peach St', 'city': 'Erie', 'zip': '16501'},
        {'street': '501 Penn St', 'city': 'Reading', 'zip': '19601'},
        {'street': '642 Main St', 'city': 'Bethlehem', 'zip': '18018'},
        {'street': '101 W Broad St', 'city': 'Bethlehem', 'zip': '18018'},
        {'street': '215 Market St', 'city': 'Scranton', 'zip': '18503'},
        {'street': '520 Spruce St', 'city': 'Scranton', 'zip': '18503'},
    ]
    
    name = f"{first_name} {last_name}"
    psu_id = psu_id_func()
    selected = random.choice(college_majors)
    college = selected['college']
    major = selected['major']
    addr = random.choice(pa_addresses)
    street = addr['street']
    city_info = {'city': addr['city'], 'zip': addr['zip']}
    
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    
    # Load Penn State logo as base64
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    
    logo_path = os.path.join(assets_dir, 'psu_logo.png')
    try:
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
        logo_img = f'<img src="data:image/png;base64,{logo_base64}" alt="Penn State" style="height: 70px;">'
    except FileNotFoundError:
        logo_img = '<div style="font-size: 32pt; font-weight: bold; color: #1e407c;">PennState</div>'
    
    # Load signature as base64
    sig_path = os.path.join(assets_dir, 'signature.png')
    try:
        with open(sig_path, 'rb') as f:
            sig_base64 = base64.b64encode(f.read()).decode('utf-8')
        sig_img = f'<img src="data:image/png;base64,{sig_base64}" alt="Signature" style="height: 45px; margin: 5px 0;">'
    except FileNotFoundError:
        sig_img = ''
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Times New Roman', Times, Georgia, serif;
            background: white;
            color: #000;
            font-size: 11pt;
            line-height: 1.4;
        }}
        
        .letter-container {{
            width: 8.5in;
            min-height: 11in;
            padding: 0.6in 0.75in;
            background: white;
        }}
        
        .header {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 30px;
        }}
        
        .header-logo {{
            flex: 0 0 auto;
            margin-right: 25px;
        }}
        
        .header-center {{
            flex: 1;
            font-size: 10.5pt;
            line-height: 1.3;
            color: #224586;
        }}
        
        .header-center .dept {{
            color: #224586;
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 2px;
        }}
        
        .header-right {{
            flex: 0 0 auto;
            text-align: left;
            font-size: 10pt;
            color: #224586;
            line-height: 1.35;
            margin-left: 30px;
        }}
        
        .date-offer-section {{
            display: flex;
            margin: 20px 0 15px 0;
        }}
        
        .left-column {{
            flex: 0 0 200px;
        }}
        
        .date {{
            margin-bottom: 20px;
        }}
        
        .student-address {{
            line-height: 1.35;
        }}
        
        .offer-details {{
            flex: 1;
        }}
        
        .offer-details-title {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 11pt;
        }}
        
        .offer-details-content {{
            font-size: 10pt;
            line-height: 1.35;
        }}
        
        .offer-details-content span.value {{
            font-weight: bold;
        }}
        
        .salutation {{
            margin-bottom: 15px;
        }}
        
        .body-text {{
            text-align: justify;
            margin-bottom: 12px;
            line-height: 1.35;
        }}
        
        .body-text strong {{
            font-weight: bold;
        }}
        
        .body-text em {{
            font-style: italic;
        }}
        
        .signature-block {{
            margin-top: 20px;
        }}
        
        .signature-name {{
            font-weight: normal;
            margin-top: 0;
        }}
        
        .signature-title {{
            font-size: 10.5pt;
        }}
    </style>
</head>
<body>

<div class="letter-container">
    <div class="header">
        <div class="header-logo">
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
    
    <div class="date-offer-section">
        <div class="left-column">
            <div class="date">{date_str}</div>
            <div class="student-address">
                {name}<br>
                {street}<br>
                {city_info['city']}, PA {city_info['zip']}
            </div>
        </div>
        <div class="offer-details">
            <div class="offer-details-title">Offer of Admission Details</div>
            <div class="offer-details-content">
                Penn State ID: <span class="value">{psu_id}</span><br>
                Campus: <span class="value">University Park</span><br>
                Term: <span class="value">Spring 2026</span><br>
                College: <span class="value">{college}</span><br>
                Intended Major: <span class="value">{major}</span><br>
                Residency: <span class="value">Non-Resident (Out of State)</span>
            </div>
        </div>
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
        Once you have paid your acceptance fees, the Directorate of International Students and Scholars Advising
        (DISSA) will contact you regarding visa documents (I-20 or DS-2019), and financial guarantee information.
        Please watch for emails from <em>international@psu.edu</em>. Orientation and other pre-arrival information will also be
        emailed to you at or around this same time.
    </div>
    
    <div class="body-text">
        As you consider your college options, I encourage you to learn more about what Penn State can offer 
        you by visiting <strong>admissions.psu.edu/accepted</strong>.
    </div>
    
    <div class="body-text">
        Congratulations, and welcome to Penn State!
    </div>
    
    <div class="signature-block">
        Sincerely,<br><br>
        {sig_img}
        <div class="signature-name">Robert G. Springall</div>
        <div class="signature-title">Executive Director of Undergraduate Admissions</div>
    </div>
</div>

</body>
</html>
"""
    return html


def generate_offer_letter_html_with_data(first_name, last_name, psu_id, college, major):
    """
    Generate Penn State Offer of Admission Details HTML with FIXED data.
    
    Used for consistency when generating both LionPATH and Offer Letter together.
    
    Args:
        first_name: Student first name
        last_name: Student last name
        psu_id: Fixed PSU ID (same as LionPATH)
        college: Fixed college name
        major: Fixed major name
    
    Returns:
        str: HTML content
    """
    # Real Pennsylvania addresses
    pa_addresses = [
        {'street': '1247 Murray Ave', 'city': 'Pittsburgh', 'zip': '15217'},
        {'street': '5801 Forbes Ave', 'city': 'Pittsburgh', 'zip': '15217'},
        {'street': '1520 Locust St', 'city': 'Philadelphia', 'zip': '19102'},
        {'street': '3401 Walnut St', 'city': 'Philadelphia', 'zip': '19104'},
        {'street': '301 Market St', 'city': 'Harrisburg', 'zip': '17101'},
        {'street': '129 S Allen St', 'city': 'State College', 'zip': '16801'},
        {'street': '411 S Burrowes St', 'city': 'State College', 'zip': '16801'},
        {'street': '720 Maple Ave', 'city': 'DuBois', 'zip': '15801'},
        {'street': '45 N 3rd St', 'city': 'Allentown', 'zip': '18101'},
        {'street': '300 State St', 'city': 'Erie', 'zip': '16501'},
        {'street': '501 Penn St', 'city': 'Reading', 'zip': '19601'},
        {'street': '642 Main St', 'city': 'Bethlehem', 'zip': '18018'},
        {'street': '215 Market St', 'city': 'Scranton', 'zip': '18503'},
    ]
    
    name = f"{first_name} {last_name}"
    addr = random.choice(pa_addresses)
    street = addr['street']
    city_info = {'city': addr['city'], 'zip': addr['zip']}
    
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    
    # Load Penn State logo as base64
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    
    logo_path = os.path.join(assets_dir, 'psu_logo.png')
    try:
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
        logo_img = f'<img src="data:image/png;base64,{logo_base64}" alt="Penn State" style="height: 70px;">'
    except FileNotFoundError:
        logo_img = '<div style="font-size: 32pt; font-weight: bold; color: #1e407c;">PennState</div>'
    
    # Load signature as base64
    sig_path = os.path.join(assets_dir, 'signature.png')
    try:
        with open(sig_path, 'rb') as f:
            sig_base64 = base64.b64encode(f.read()).decode('utf-8')
        sig_img = f'<img src="data:image/png;base64,{sig_base64}" alt="Signature" style="height: 45px; margin: 5px 0;">'
    except FileNotFoundError:
        sig_img = ''
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Times New Roman', Times, Georgia, serif;
            background: white;
            color: #000;
            font-size: 11pt;
            line-height: 1.4;
        }}
        
        .letter-container {{
            width: 8.5in;
            min-height: 11in;
            padding: 0.6in 0.75in;
            background: white;
        }}
        
        .header {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 30px;
        }}
        
        .header-logo {{
            flex: 0 0 auto;
            margin-right: 25px;
        }}
        
        .header-center {{
            flex: 1;
            font-size: 10.5pt;
            line-height: 1.3;
            color: #224586;
        }}
        
        .header-center .dept {{
            color: #224586;
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 2px;
        }}
        
        .header-right {{
            flex: 0 0 auto;
            text-align: left;
            font-size: 10pt;
            color: #224586;
            line-height: 1.35;
            margin-left: 30px;
        }}
        
        .date-offer-section {{
            display: flex;
            margin: 20px 0 15px 0;
        }}
        
        .left-column {{
            flex: 0 0 200px;
        }}
        
        .date {{
            margin-bottom: 20px;
        }}
        
        .student-address {{
            line-height: 1.35;
        }}
        
        .offer-details {{
            flex: 1;
        }}
        
        .offer-details-title {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 11pt;
        }}
        
        .offer-details-content {{
            font-size: 10pt;
            line-height: 1.35;
        }}
        
        .offer-details-content span.value {{
            font-weight: bold;
        }}
        
        .salutation {{
            margin-bottom: 15px;
        }}
        
        .body-text {{
            text-align: justify;
            margin-bottom: 12px;
            line-height: 1.35;
        }}
        
        .body-text strong {{
            font-weight: bold;
        }}
        
        .body-text em {{
            font-style: italic;
        }}
        
        .signature-block {{
            margin-top: 20px;
        }}
        
        .signature-name {{
            font-weight: normal;
            margin-top: 0;
        }}
        
        .signature-title {{
            font-size: 10.5pt;
        }}
    </style>
</head>
<body>

<div class="letter-container">
    <div class="header">
        <div class="header-logo">
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
    
    <div class="date-offer-section">
        <div class="left-column">
            <div class="date">{date_str}</div>
            <div class="student-address">
                {name}<br>
                {street}<br>
                {city_info['city']}, PA {city_info['zip']}
            </div>
        </div>
        <div class="offer-details">
            <div class="offer-details-title">Offer of Admission Details</div>
            <div class="offer-details-content">
                Penn State ID: <span class="value">{psu_id}</span><br>
                Campus: <span class="value">University Park</span><br>
                Term: <span class="value">Spring 2026</span><br>
                College: <span class="value">{college}</span><br>
                Intended Major: <span class="value">{major}</span><br>
                Residency: <span class="value">Non-Resident (Out of State)</span>
            </div>
        </div>
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
        Once you have paid your acceptance fees, the Directorate of International Students and Scholars Advising
        (DISSA) will contact you regarding visa documents (I-20 or DS-2019), and financial guarantee information.
        Please watch for emails from <em>international@psu.edu</em>. Orientation and other pre-arrival information will also be
        emailed to you at or around this same time.
    </div>
    
    <div class="body-text">
        As you consider your college options, I encourage you to learn more about what Penn State can offer 
        you by visiting <strong>admissions.psu.edu/accepted</strong>.
    </div>
    
    <div class="body-text">
        Congratulations, and welcome to Penn State!
    </div>
    
    <div class="signature-block">
        Sincerely,<br><br>
        {sig_img}
        <div class="signature-name">Robert G. Springall</div>
        <div class="signature-title">Executive Director of Undergraduate Admissions</div>
    </div>
</div>

</body>
</html>
"""
    return html

