"""Global configuration file"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "pk_oa")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/pk_oa")

# Admin configuration
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))

# Points configuration
VERIFY_COST = 1  # Points consumed per verification
CHECKIN_REWARD = 1  # Daily check-in reward points
INVITE_REWARD = 2  # Invite reward points
REGISTER_REWARD = 1  # Registration reward points

# Help link
HELP_NOTION_URL = "https://rhetorical-era-3f3.notion.site/dd78531dbac745af9bbac156b51da9cc"
