# Telegram Session & Config

## Files
- `telegram_session.session` - Telethon session file (đã xác thực)
- `config.json` - API credentials và bot settings

## API Credentials
```json
{
    "api_id": "37410686",
    "api_hash": "7fa9edad48b082bbbddd84c7a4ac581e"
}
```

## Temp Email Bots

### @TempMail_org_bot (Recommended)
```
/start - Get initial email
/new   - Create new email
/list  - List all emails
```

### @bjfreemail_bot (Chinese - may not work)
```
/new     - Create new email
/address - List emails
/delete  - Delete email
```

## Usage Example
```python
from telethon import TelegramClient

SESSION_FILE = "telegram/telegram_session"
API_ID = "37410686"
API_HASH = "7fa9edad48b082bbbddd84c7a4ac581e"

client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
await client.start()
```
