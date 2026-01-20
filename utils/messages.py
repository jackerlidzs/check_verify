"""Message templates"""
from settings import CHANNEL_URL, VERIFY_COST, HELP_NOTION_URL


def get_welcome_message(full_name: str, invited_by: bool = False) -> str:
    """Get welcome message"""
    msg = (
        f"🎉 Welcome, {full_name}!\n"
        "You have successfully registered and received 1 point.\n"
    )
    if invited_by:
        msg += "Thank you for joining via invite link, the inviter has received 2 points.\n"

    msg += (
        "\nThis bot can automatically complete SheerID verification.\n"
        "Quick start:\n"
        "/about - Learn about bot features\n"
        "/balance - Check your points balance\n"
        "/help - View complete command list\n\n"
        "Get more points:\n"
        "/qd - Daily check-in\n"
        "/invite - Invite friends\n"
        f"Join channel: {CHANNEL_URL}"
    )
    return msg


def get_about_message() -> str:
    """Get about message"""
    return (
        "🤖 SheerID Auto Verification Bot\n"
        "\n"
        "Features:\n"
        "- Automatically complete SheerID student/teacher/military verification\n"
        "- Supports Gemini One Pro, ChatGPT Teacher K12, Spotify Student, YouTube Student, Bolt.new Teacher, ChatGPT Military verification\n"
        "\n"
        "How to get points:\n"
        "- Registration bonus: 1 point\n"
        "- Daily check-in: +1 point\n"
        "- Invite friends: +2 points/person\n"
        "- Use card keys (according to key rules)\n"
        f"- Join channel: {CHANNEL_URL}\n"
        "\n"
        "How to use:\n"
        "1. Start verification on the website and copy the complete verification link\n"
        "2. Send /verify, /verify2, /verify3, /verify4, /verify5 or /verify6 with the link\n"
        "3. Wait for processing and check the result\n"
        "4. Bolt.new verification will automatically get the code, use /getV4Code <verification_id> for manual query\n"
        "\n"
        "For more commands, send /help"
    )


def get_help_message(is_admin: bool = False) -> str:
    """Get help message"""
    msg = (
        "📖 SheerID Auto Verification Bot - Help\n"
        "\n"
        "User Commands:\n"
        "/start - Start using (register)\n"
        "/about - Learn about bot features\n"
        "/balance - Check points balance\n"
        "/qd - Daily check-in (+1 point)\n"
        "/invite - Generate invite link (+2 points/person)\n"
        "/use <card_key> - Use card key to redeem points\n"
        f"/verify <link> - Gemini One Pro verification (-{VERIFY_COST} points)\n"
        f"/verify2 <link> - ChatGPT Teacher K12 verification (-{VERIFY_COST} points)\n"
        f"/verify3 <link> - Spotify Student verification (-{VERIFY_COST} points)\n"
        f"/verify4 <link> - Bolt.new Teacher verification (-{VERIFY_COST} points)\n"
        f"/verify5 <link> - YouTube Student Premium verification (-{VERIFY_COST} points)\n"
        f"/verify6 <link> - ChatGPT Military verification (-{VERIFY_COST} points, email in chat)\n"
        "/getV4Code <verification_id> - Get Bolt.new verification code\n"
        "/checkStatus <verification_id> - Check SheerID verification status\n"
        "/help - View this help information\n"
        f"Verification failure help: {HELP_NOTION_URL}\n"
    )

    if is_admin:
        msg += (
            "\nAdmin Commands:\n"
            "/addbalance <user_id> <points> - Add user points\n"
            "/block <user_id> - Block user\n"
            "/white <user_id> - Unblock user\n"
            "/blacklist - View blacklist\n"
            "/genkey <key> <points> [uses] [days] - Generate card key\n"
            "/listkeys - View card key list\n"
            "/broadcast <text> - Send notification to all users\n"
        )

    return msg


def get_insufficient_balance_message(current_balance: int) -> str:
    """Get insufficient balance message"""
    return (
        f"Insufficient points! Need {VERIFY_COST} points, current balance: {current_balance} points.\n\n"
        "How to get points:\n"
        "- Daily check-in /qd\n"
        "- Invite friends /invite\n"
        "- Use card key /use <card_key>"
    )


def get_verify_usage_message(command: str, service_name: str) -> str:
    """Get verification command usage message"""
    return (
        f"Usage: {command} <SheerID_link>\n\n"
        "Example:\n"
        f"{command} https://services.sheerid.com/verify/xxx/?verificationId=xxx\n\n"
        "How to get verification link:\n"
        f"1. Visit {service_name} verification page\n"
        "2. Start the verification process\n"
        "3. Copy the complete URL from browser address bar\n"
        f"4. Submit using {command} command"
    )
