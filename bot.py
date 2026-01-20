"""Telegram Bot Main Program"""
import logging

# Reduce httpx log spam (getUpdates, etc.)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
from functools import partial

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from settings import BOT_TOKEN


# Bot commands menu - shown when user clicks Menu button
BOT_COMMANDS = [
    BotCommand("start", "Bắt đầu / Start"),
    BotCommand("help", "Trợ giúp / Help & commands"),
    BotCommand("me", "Thông tin cá nhân / Profile"),
    BotCommand("balance", "Số dư điểm / Points balance"),
    BotCommand("qd", "Điểm danh hàng ngày / Daily check-in"),
    BotCommand("invite", "Link mời bạn bè / Invite friends"),
    BotCommand("use", "Dùng card key / Use card key"),
    BotCommand("verify", "Google One Pro (Student)"),
    BotCommand("verify2", "ChatGPT Plus (K12 Teacher)"),
    BotCommand("verify3", "Spotify Premium (Student)"),
    BotCommand("verify4", "Bolt.new Pro (Teacher)"),
    BotCommand("verify6", "Military Verification"),
    BotCommand("checkstatus", "Kiểm tra trạng thái / Check status"),
]
from database_mysql import Database
from handlers.user_commands import (
    start_command,
    about_command,
    help_command,
    balance_command,
    me_command,
    checkin_command,
    invite_command,
    use_command,
)
from handlers.verify_commands import (
    verify_command,
    verify2_command,
    verify2_cookie_handler,
    verify3_command,
    verify4_command,
    getV4Code_command,
    verify6_command,
    verify6_email_handler,
    checkStatus_command,
)
from handlers.admin_commands import (
    addbalance_command,
    block_command,
    white_command,
    blacklist_command,
    genkey_command,
    listkeys_command,
    broadcast_command,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """Global error handler"""
    logger.exception("Exception occurred while processing update: %s", context.error, exc_info=context.error)


def main():
    """Main function"""
    # Initialize database
    db = Database()

    async def post_init(application):
        """Set bot commands after initialization"""
        await application.bot.set_my_commands(BOT_COMMANDS)
        logger.info("✅ Bot menu commands set successfully")

    # Create application - enable concurrent processing
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)  # 🔥 Key: Enable concurrent processing of multiple commands
        .post_init(post_init)  # 📋 Set menu commands on startup
        .build()
    )

    # Register user commands (using partial to pass db parameter)
    application.add_handler(CommandHandler("start", partial(start_command, db=db)))
    application.add_handler(CommandHandler("about", partial(about_command, db=db)))
    application.add_handler(CommandHandler("help", partial(help_command, db=db)))
    application.add_handler(CommandHandler("balance", partial(balance_command, db=db)))
    application.add_handler(CommandHandler("me", partial(me_command, db=db)))
    application.add_handler(CommandHandler("qd", partial(checkin_command, db=db)))
    application.add_handler(CommandHandler("invite", partial(invite_command, db=db)))
    application.add_handler(CommandHandler("use", partial(use_command, db=db)))

    # Register verification commands
    application.add_handler(CommandHandler("verify", partial(verify_command, db=db)))
    application.add_handler(CommandHandler("verify2", partial(verify2_command, db=db)))
    application.add_handler(CommandHandler("verify3", partial(verify3_command, db=db)))
    application.add_handler(CommandHandler("verify4", partial(verify4_command, db=db)))
    application.add_handler(CommandHandler("getV4Code", partial(getV4Code_command, db=db)))
    application.add_handler(CommandHandler("verify6", partial(verify6_command, db=db)))
    application.add_handler(CommandHandler("checkStatus", partial(checkStatus_command, db=db)))
    application.add_handler(CommandHandler("checkstatus", partial(checkStatus_command, db=db)))  # Lowercase alias for menu

    # Register admin commands
    application.add_handler(CommandHandler("addbalance", partial(addbalance_command, db=db)))
    application.add_handler(CommandHandler("block", partial(block_command, db=db)))
    application.add_handler(CommandHandler("white", partial(white_command, db=db)))
    application.add_handler(CommandHandler("blacklist", partial(blacklist_command, db=db)))
    application.add_handler(CommandHandler("genkey", partial(genkey_command, db=db)))
    application.add_handler(CommandHandler("listkeys", partial(listkeys_command, db=db)))
    application.add_handler(CommandHandler("broadcast", partial(broadcast_command, db=db)))

    # Register message handler for email replies (military verification) and cookie paste
    async def handle_text_message(update, context):
        """Handle text messages - check for pending verifications"""
        # Check for pending K12 cookie verification
        handled = await verify2_cookie_handler(update, context, db)
        if handled:
            return
        # Check for pending military verification email
        handled = await verify6_email_handler(update, context, db)
        if handled:
            return
        # Message not handled - could add other handlers here
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
