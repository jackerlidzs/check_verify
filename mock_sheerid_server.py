from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import os
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mock Data
PROGRAM_ID = '68d47554aa292d20b9bec8f7'

# Templates
FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your status</title>
    <style>
        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #f9f9fa;
            color: #333;
            display: flex;
            justify_content: center;
            padding-top: 50px;
            margin: 0;
        }
        .container {
            background: white;
            width: 100%;
            max_width: 900px;
            padding: 40px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-radius: 4px;
        }
        h1 {
            font-size: 24px;
            text-align: center;
            margin-bottom: 10px;
            color: #000;
        }
        .subtitle {
            text-align: center;
            color: #0056b3;
            font-size: 14px;
            margin-bottom: 30px;
            cursor: pointer;
        }
        .required-note {
            font-size: 13px;
            color: #666;
            margin-bottom: 15px;
        }
        .form-group {
            margin-bottom: 20px;
            position: relative;
        }
        label {
            display: block;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
            color: #333;
        }
        input[type="text"], input[type="email"], input[type="date"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }
        input:focus {
            border-color: #0056b3;
            outline: none;
        }
        .helper-text {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
        button {
            width: 100%;
            padding: 15px;
            background-color: #4a5c6e;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background-color: #3a4856;
        }

        /* Dropdown Styles */
        .org-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ccc;
            border-top: none;
            z-index: 10;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .sid-org-result {
            padding: 10px;
            cursor: pointer;
            font-size: 14px;
        }
        .sid-org-result:hover {
            background-color: #f1f1f1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Verify you're a teacher, administrator, or district leader at an accredited K-12 institution.</h1>
        <div class="subtitle">How does verifying work?</div>
        
        <div class="required-note">* Required information</div>
        
        <form method="POST" action="/verify/{{ program_id }}/submit">
            <input type="hidden" name="verificationId" value="{{ verification_id }}">
            
            <!-- School Name (First, as requested) -->
            <div class="form-group">
                <label>School name*</label>
                <input type="text" name="organization" id="orgInput" autocomplete="off" placeholder="Type to search...">
                <div id="orgResults" class="org-results"></div>
            </div>

            <!-- First Name -->
            <div class="form-group">
                <label>First name*</label>
                <input type="text" name="firstName" required>
            </div>
            
            <!-- Last Name -->
            <div class="form-group">
                <label>Last name*</label>
                <input type="text" name="lastName" required>
            </div>
            
            <!-- Email -->
            <div class="form-group">
                <label>Email address*</label>
                <div class="helper-text" style="margin-bottom: 5px;">Must be your school-issued email address</div>
                <input type="email" name="email" required>
            </div>
            
            <!-- Birth Date (Hidden in UI usually till next step or just separate, but keep simplified here) -->
            <div class="form-group">
                <label>Birth Date*</label>
                <input type="date" name="birthDate" required value="1985-01-01">
            </div>
            
            <button type="submit">Verify My Educator Status</button>
        </form>
    </div>

    <script>
        // Mock School Data
        const schools = [
            "Springfield High School",
            "Springfield Central High School",
            "Bronx High School of Science",
            "Brooklyn Technical High School",
            "Stuyvesant High School",
            "Miami Palmetto Senior High School",
            "Coral Reef Senior High School",
            "South Dade Middle School"
        ];

        const orgInput = document.getElementById('orgInput');
        const orgResults = document.getElementById('orgResults');

        orgInput.addEventListener('input', function() {
            const val = this.value.toLowerCase();
            orgResults.innerHTML = '';
            
            if (!val) {
                orgResults.style.display = 'none';
                return;
            }

            const matches = schools.filter(s => s.toLowerCase().includes(val));
            
            if (matches.length > 0) {
                matches.forEach(school => {
                    const div = document.createElement('div');
                    div.className = 'sid-org-result';
                    div.textContent = school;
                    div.onclick = function() {
                        orgInput.value = school;
                        orgResults.style.display = 'none';
                    };
                    orgResults.appendChild(div);
                });
                orgResults.style.display = 'block';
            } else {
                orgResults.style.display = 'none';
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== orgInput) {
                orgResults.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

UPLOAD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Upload Document</title>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9fa; display: flex; justify-content: center; padding-top: 50px; }
        .container { background: white; width: 100%; max_width: 500px; padding: 40px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { font-size: 24px; text-align: center; }
        .upload-area { border: 2px dashed #ccc; padding: 30px; text-align: center; margin: 20px 0; border-radius: 4px; }
        button { width: 100%; padding: 15px; background-color: #4a5c6e; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload a document</h1>
        <p style="text-align: center; color: #666;">Please upload a school ID card or pay stub.</p>
        
        <form method="POST" action="/verify/{{ program_id }}/upload" enctype="multipart/form-data">
            <input type="hidden" name="verificationId" value="{{ verification_id }}">
            
            <div class="upload-area">
                <input type="file" name="file"><br>
            </div>
            
            <button type="submit">Submit Document</button>
        </form>
    </div>
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Success</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
    <h1 style="color: green;">Verification Successful!</h1>
    <p>You have been verified.</p>
    <a href="https://chatgpt.com/education?token=mock_token">Click here to claim your offer</a>
</body>
</html>
"""

@app.route(f'/verify/{PROGRAM_ID}/', methods=['GET'])
def start_verify():
    verification_id = str(uuid.uuid4().hex)
    return render_template_string(FORM_TEMPLATE, program_id=PROGRAM_ID, verification_id=verification_id)

@app.route(f'/verify/{PROGRAM_ID}/submit', methods=['POST'])
def submit_form():
    return redirect(url_for('upload_page', verificationId=request.form.get('verificationId')))

@app.route(f'/verify/{PROGRAM_ID}/docUpload', methods=['GET'])
def upload_page():
    verification_id = request.args.get('verificationId', 'mock_id')
    return render_template_string(UPLOAD_TEMPLATE, program_id=PROGRAM_ID, verification_id=verification_id)

@app.route(f'/verify/{PROGRAM_ID}/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return redirect(url_for('success_page'))

@app.route('/verify/success', methods=['GET'])
def success_page():
    return render_template_string(SUCCESS_TEMPLATE)

if __name__ == '__main__':
    print(f"Mock Server running on http://localhost:5000/verify/{PROGRAM_ID}/")
    app.run(port=5000, debug=True)
