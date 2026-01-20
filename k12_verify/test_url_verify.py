"""Test URL Verifier with Proxy"""
import os
import sys
sys.path.insert(0, r'c:\Users\jacke\Desktop\tgbot-verify\k12_verify')
os.chdir(r'c:\Users\jacke\Desktop\tgbot-verify\k12_verify')

from app.core.url_verifier import URLVerifier

url = 'https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=696294d967a9f2698e86db4b'

def status_callback(step, msg):
    print(f'[{step}] {msg}')

print('='*50)
print('URL Verifier Test with Proxy')
print('='*50)

verifier = URLVerifier(
    verification_url=url,
    custom_email='test@yopmail.com',
    status_callback=status_callback
)

print(f'Verification ID: {verifier.verification_id}')
print(f'IP: {verifier.current_ip} ({verifier.ip_country})')

# Test browser config
config = verifier._get_random_browser_config()
print(f'UA: {config["user_agent"][:60]}...')
print(f'Sec-Ch-Ua: {config["sec_ch_ua"]}')
print(f'Platform: {config["platform"]}')

# Check status
print('\nChecking verification status...')
status = verifier._check_status()
print(f'Status Code: {status.get("status_code")}')
print(f'Current Step: {status.get("data", {}).get("currentStep", "unknown")}')

# Run full verification if status is good
data = status.get('data', {})
current_step = data.get('currentStep', '')
print(f'\nCurrent step: {current_step}')

if current_step == 'success':
    print('✅ Already verified!')
elif current_step == 'error':
    print(f'❌ Error: {data.get("errorMessage", "Unknown")}')
elif current_step in ['collectTeacherPersonalInfo', 'pending', 'docUpload']:
    print(f'📋 Ready for verification (step: {current_step})')
    print('\nStarting full verification...')
    result = verifier.verify()
    print(f'\nResult: {result}')
else:
    print(f'⚠️ Unexpected step: {current_step}')
    print(f'Full data: {data}')
