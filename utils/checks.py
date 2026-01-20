"""Permission checks and validation utilities"""
import logging
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from settings import CHANNEL_USERNAME

logger = logging.getLogger(__name__)


def is_group_chat(update: Update) -> bool:
    """Check if this is a group chat"""
    chat = update.effective_chat
    return chat and chat.type in ("group", "supergroup")


async def reject_group_command(update: Update) -> bool:
    """Group chat restriction: Only allow /verify /verify2 /verify3 /verify4 /verify5 /qd"""
    if is_group_chat(update):
        await update.message.reply_text("Group chat only supports /verify /verify2 /verify3 /verify4 /verify5 /qd. Please use other commands in private chat.")
        return True
    return False


async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the channel"""
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError as e:
        logger.error("Failed to check channel membership: %s", e)
        return False
