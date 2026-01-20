"""User command handlers"""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command
from utils.messages import (
    get_welcome_message,
    get_about_message,
    get_help_message,
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /start command"""
    if await reject_group_command(update):
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    full_name = user.full_name or ""

    # Already initialized, return directly
    if db.user_exists(user_id):
        await update.message.reply_text(
            f"Welcome back, {full_name}!\n"
            "You have already registered.\n"
            "Send /help to view available commands."
        )
        return

    # Invite participation
    invited_by: Optional[int] = None
    if context.args:
        try:
            invited_by = int(context.args[0])
            if not db.user_exists(invited_by):
                invited_by = None
        except Exception:
            invited_by = None

    # Create user
    if db.create_user(user_id, username, full_name, invited_by):
        welcome_msg = get_welcome_message(full_name, bool(invited_by))
        await update.message.reply_text(welcome_msg)
    else:
        await update.message.reply_text("Registration failed, please try again later.")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /about command"""
    if await reject_group_command(update):
        return

    await update.message.reply_text(get_about_message())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /help command"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_USER_ID
    await update.message.reply_text(get_help_message(is_admin))


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /balance command"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please register first using /start.")
        return

    await update.message.reply_text(
        f"💰 Points Balance\n\nCurrent points: {user['balance']} pts"
    )


async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /me command - Show user profile"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    tg_user = update.effective_user

    if db.is_user_blocked(user_id):
        await update.message.reply_text("❌ Tài khoản của bạn đã bị khóa.")
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("⚠️ Vui lòng đăng ký trước bằng /start")
        return

    # Build profile message
    profile_msg = (
        f"👤 **Thông tin cá nhân**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📛 Tên: {tg_user.full_name}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"👤 Username: @{tg_user.username or 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Số dư: **{user['balance']}** điểm\n"
        f"📅 Ngày đăng ký: {user.get('created_at', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 Kiếm thêm điểm:\n"
        f"• /qd - Điểm danh hàng ngày (+1)\n"
        f"• /invite - Mời bạn bè (+2)\n"
        f"• /use <key> - Dùng card key"
    )
    
    await update.message.reply_text(profile_msg, parse_mode="Markdown")


async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /qd check-in command - Temporarily disabled"""
    user_id = update.effective_user.id

    # Temporarily disable check-in feature (fixing bug)
    # await update.message.reply_text(
    #     "⚠️ Check-in feature is temporarily under maintenance\n\n"
    #     "Due to a bug, check-in is temporarily closed for fixing.\n"
    #     "Expected to resume soon, sorry for the inconvenience.\n\n"
    #     "💡 You can get points through:\n"
    #     "• Invite friends /invite (+2 points)\n"
    #     "• Use card key /use <card_key>"
    # )
    # return
    
    # ===== Code below is disabled =====
    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    # Layer 1 check: At command handler level
    if not db.can_checkin(user_id):
        await update.message.reply_text("❌ You have already checked in today, come back tomorrow.")
        return

    # Layer 2 check: At database level (SQL atomic operation)
    if db.checkin(user_id):
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"✅ Check-in successful!\nPoints earned: +1\nCurrent points: {user['balance']} pts"
        )
    else:
        # If database level returns False, already checked in today (double protection)
        await update.message.reply_text("❌ You have already checked in today, come back tomorrow.")


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /invite command"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
        f"🎁 Your exclusive invite link:\n{invite_link}\n\n"
        "For each successful registration, you will earn 2 points."
    )


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /use command - Use card key"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /use <card_key>\n\nExample: /use wandouyu"
        )
        return

    key_code = context.args[0].strip()
    result = db.use_card_key(key_code, user_id)

    if result is None:
        await update.message.reply_text("Card key does not exist, please check and try again.")
    elif result == -1:
        await update.message.reply_text("This card key has reached its usage limit.")
    elif result == -2:
        await update.message.reply_text("This card key has expired.")
    elif result == -3:
        await update.message.reply_text("You have already used this card key.")
    else:
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"Card key used successfully!\nPoints earned: {result}\nCurrent points: {user['balance']}"
        )
