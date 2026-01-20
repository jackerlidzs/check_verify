# ChatGPT Account Creator

Automated ChatGPT account creation using Playwright Stealth and Telegram temp emails.

## Features
- 🔒 **Playwright Stealth** - Bypass Cloudflare bot detection
- 📧 **Telegram Temp Email** - Auto receive verification codes
- 🌐 **Proxy Support** - ISP/Residential proxy support
- 🤖 **Full Automation** - One command to create accounts

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## First Time Setup

1. Run the script once to authenticate Telegram:
```bash
python full_automation.py
```

2. Enter your phone number when prompted
3. Enter the verification code from Telegram
4. Session will be saved for future use

## Usage

### Full Automation (Recommended)
```bash
# Create 1 account without proxy
python full_automation.py --no-proxy

# Create 1 account with proxy
python full_automation.py

# Create multiple accounts
python full_automation.py --num 5

# Cleanup temp emails
python full_automation.py --cleanup
```

### Manual Email Signup
```bash
# If you have your own email
python stealth_signup.py --email your@email.com --password YourPass123!
```

## Configuration

Edit `config.json`:

```json
{
    "telegram": {
        "api_id": "YOUR_API_ID",
        "api_hash": "YOUR_API_HASH",
        "bot_username": "TempMail_org_bot"
    },
    "proxy": {
        "enabled": true,
        "host": "proxy.example.com",
        "port": 8080,
        "username": "user",
        "password": "pass"
    }
}
```

### Get Telegram API Credentials
1. Go to https://my.telegram.org
2. Login with your phone
3. Create new application
4. Copy API ID and API Hash

## Files

```
chatgpt/
├── config.json          # Configuration
├── requirements.txt     # Dependencies
├── full_automation.py   # Main script (temp email + signup)
├── stealth_signup.py    # Manual email signup
├── auth0_signup.py      # API-only (doesn't work - Cloudflare)
└── data/
    ├── telegram_session.session  # Telegram auth session
    ├── accounts.json             # Created accounts
    └── screenshots/              # Signup screenshots
```

## Output

Created accounts are saved to `data/accounts.json`:
```json
{
    "accounts": [
        {
            "email": "temp123@example.com",
            "password": "GeneratedPass123!",
            "created_at": "2026-01-09T10:00:00",
            "status": "active"
        }
    ]
}
```

## Troubleshooting

### Cloudflare Challenge
- Wait for the challenge to complete (auto-handled by stealth)
- Try using ISP proxy instead of datacenter

### Telegram Auth Failed
- Delete `data/telegram_session.session`
- Run again to re-authenticate

### Email Not Received
- Check if @TempMail_org_bot is working
- Try /start command in bot manually

## License
For educational purposes only.
