"""Quick test for cookie verifier"""
import json

cookies_json = '''[
    {
        "domain": "services.sheerid.com",
        "name": "JSESSIONID",
        "value": "8mWvvpTwDfaNoS5VO1JcYYYfET-3Jk5oJoKKAIeW82gOzpwyBGeVFKLTqscmJ2iYzi6Gk439mJIStJnelmfo16vKnuhN85lGArB5SR7VLPljA7VLZbM9yoWfzjEeSa_VitrEJg__.core-platform-sheerid-84f54cc6bf-7cmwc"
    },
    {
        "domain": "services.sheerid.com",
        "name": "AWSALBCORS",
        "value": "klwb9kHRQhGZFZwSNNizNY8oOf7Sabr5fSeDNlh0rd8hs2cqst07gwDcAiACW0gx33iID1uRiOzikmw/9rRBlXF52ov5V6BSzlxlRiJdDB1XllgweRpAczpLrYhc"
    },
    {
        "domain": "services.sheerid.com",
        "name": "sid-verificationId",
        "value": "694eddb6dc2d116d71690164"
    }
]'''

from k12.cookie_verifier import parse_cookie_json, CookieVerifier, extract_verification_id

cookies = parse_cookie_json(cookies_json)
print('Parsed cookies:', list(cookies.keys()))
print('Verification ID:', extract_verification_id(cookies))

verifier = CookieVerifier(cookies)
status = verifier.check_status()
print('\n=== API Response ===')
print('Current step:', status.get('current_step'))
print('Status code:', status.get('status_code'))
print('Full data:', json.dumps(status.get('data'), indent=2))
