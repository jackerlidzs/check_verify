"""Verification command handlers"""
import asyncio
import logging
import httpx
import time
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from settings import VERIFY_COST
from database_mysql import Database
from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from youtube.sheerid_verifier import SheerIDVerifier as YouTubeVerifier
from Boltnew.sheerid_verifier import SheerIDVerifier as BoltnewVerifier
from military.sheerid_verifier import SheerIDVerifier as MilitaryVerifier
from utils.messages import get_insufficient_balance_message, get_verify_usage_message

# Try to import concurrency control, use empty implementation if failed
try:
    from utils.concurrency import get_verification_semaphore
except ImportError:
    # If import fails, create a simple implementation
    def get_verification_semaphore(verification_type: str):
        return asyncio.Semaphore(3)

logger = logging.getLogger(__name__)


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify command - Gemini One Pro"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify", "Gemini One Pro")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    verification_id = OneVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Invalid SheerID link, please check and try again.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    processing_msg = await update.message.reply_text(
        f"💎 Starting Gemini One Pro verification...\n"
        f"Verification ID: `{verification_id}`\n"
        f"Deducted {VERIFY_COST} points\n\n"
        "⏳ Step 0/4: Initializing...",
        parse_mode="Markdown"
    )

    # Progress tracking
    progress_queue = []
    
    def progress_callback(step: int, total: int, message: str):
        progress_queue.append((step, total, message))
    
    async def update_progress():
        """Periodically update Telegram message with progress"""
        last_step = 0
        while True:
            await asyncio.sleep(0.5)
            if progress_queue:
                step, total, msg = progress_queue[-1]
                if step != last_step:
                    try:
                        progress_bar = "▓" * step + "░" * (total - step)
                        await processing_msg.edit_text(
                            f"💎 Gemini One Pro verification\n"
                            f"ID: {verification_id[:20]}...\n\n"
                            f"⏳ Step {step}/{total}: {msg}\n"
                            f"[{progress_bar}]"
                        )
                        last_step = step
                    except Exception:
                        pass  # Ignore rate limit errors

    try:
        verifier = OneVerifier(verification_id)
        
        # Start progress updater
        progress_task = asyncio.create_task(update_progress())
        
        # Run verification with progress callback
        result = await asyncio.to_thread(verifier.verify, progress_callback=progress_callback)
        
        # Cancel progress updater
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

        db.add_verification(
            user_id,
            "gemini_one_pro",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        # Get student info for display (escape underscores for Markdown)
        student_info = result.get("student_info", {})
        profile_msg = ""
        if student_info:
            name = student_info.get('name', 'N/A')
            email = student_info.get('email', 'N/A').replace('_', '\\_')
            birth_date = student_info.get('birth_date', 'N/A')
            school = student_info.get('school', 'N/A')
            profile_msg = "\n\n📋 Student Profile Used:\n"
            profile_msg += f"• Name: {name}\n"
            profile_msg += f"• Email: {email}\n"
            profile_msg += f"• Birth Date: {birth_date}\n"
            profile_msg += f"• School: {school}"

        if result["success"]:
            result_msg = "✅ Verification successful!\n\n"
            if result.get("pending"):
                result_msg += "📄 Document submitted, awaiting manual review.\n"
            if result.get("redirect_url"):
                result_msg += f"\n👉 Redirect link:\n{result['redirect_url']}"
            result_msg += profile_msg
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            error_msg = f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
            error_msg += f"💰 Refunded {VERIFY_COST} points"
            error_msg += profile_msg
            await processing_msg.edit_text(error_msg)
    except Exception as e:
        logger.error("Verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Error during processing: {str(e)}\n\n"
            f"Refunded {VERIFY_COST} points"
        )


async def verify2_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify2 command - ChatGPT Teacher K12
    
    Usage:
        /verify2 <link> --cookies         → Prompts for cookie paste (RECOMMENDED)
        /verify2 <link> --cookies --fast  → Fast mode (no doc upload)
        /verify2 <link> --cookies [...]   → Inline cookies
        /verify2                           → Browser mode (slower)
        /verify2 <link>                    → Legacy mode (may expire)
    """
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    # Parse arguments
    import re
    custom_email = None
    cookie_json = None
    url = None
    mode = "browser"  # Default mode
    waiting_for_cookies = False
    fast_mode = False  # --fast flag for skipping doc upload
    
    # Check if user replied to a file (cookie file upload)
    cookie_file_content = None
    if update.message.reply_to_message and update.message.reply_to_message.document:
        doc = update.message.reply_to_message.document
        if doc.file_name and doc.file_name.endswith('.json'):
            try:
                file = await context.bot.get_file(doc.file_id)
                file_bytes = await file.download_as_bytearray()
                cookie_file_content = file_bytes.decode('utf-8')
                mode = "cookie"
                cookie_json = cookie_file_content
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to read cookie file: {e}")
                return
    
    if context.args:
        args_str = " ".join(context.args)
        
        # Check for -email flag
        email_match = re.search(r'-email\s+([^\s\[\]]+)', args_str, re.IGNORECASE)
        if email_match:
            potential_email = email_match.group(1)
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', potential_email):
                custom_email = potential_email
            else:
                await update.message.reply_text(
                    f"❌ Invalid email format: `{potential_email}`",
                    parse_mode="Markdown"
                )
                return
        
        # Check for URL first
        first_arg = context.args[0]
        if 'sheerid' in first_arg.lower() or 'verification' in first_arg.lower():
            url = first_arg
        
        # Check for --cookies flag
        if not cookie_file_content:
            # Check if --cookies has JSON after it
            cookie_match = re.search(r'--cookies\s+(\[[\s\S]*?\])', args_str)
            if cookie_match:
                cookie_json = cookie_match.group(1)
                mode = "cookie"
            elif '--cookies' in args_str.lower():
                # --cookies flag without JSON = wait for user to paste
                waiting_for_cookies = True
        
        # Check for --fast flag
        if '--fast' in args_str.lower() or '-fast' in args_str.lower():
            fast_mode = True
    
    # ========== 2-STEP COOKIE FLOW ==========
    if waiting_for_cookies:
        if not url:
            await update.message.reply_text(
                "❌ Please provide SheerID link:\n"
                "`/verify2 <sheerid_link> --cookies`",
                parse_mode="Markdown"
            )
            return
        
        # Store pending verification info
        context.user_data['pending_cookie_verify'] = {
            'url': url,
            'custom_email': custom_email,
            'user_id': user_id,
            'fast_mode': fast_mode,
        }
        
        fast_text = "\n⚡ **FAST MODE**: Không upload document" if fast_mode else ""
        await update.message.reply_text(
            "🍪 **Paste your cookies JSON:**\n\n"
            "1. Mở SheerID trong Chrome\n"
            "2. Click extension **EditThisCookie**\n"
            "3. Click **Export** (copy JSON)\n"
            "4. **Paste vào đây** ↓\n\n"
            f"{fast_text}\n" if fast_mode else ""
            "_Bot đang chờ cookies của bạn..._",
            parse_mode="Markdown"
        )
        return
    
    # If no mode determined yet, check for legacy URL mode
    if mode == "browser" and url and not cookie_json:
        mode = "legacy"
    
    # Check balance
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(get_insufficient_balance_message(user["balance"]))
        return

    # Deduct balance
    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    email_status = f"📧 Custom Email: `{custom_email}`\n" if custom_email else "📧 Using random teacher email\n"
    
    if mode == "cookie":
        # ========== COOKIE-BASED MODE (BEST) ==========
        processing_msg = await update.message.reply_text(
            f"🎓 **ChatGPT Teacher K12 Verification** (Cookie Mode)\n\n"
            f"{email_status}"
            f"Deducted {VERIFY_COST} points\n\n"
            "🍪 **Using your browser session...**\n"
            "This avoids 'link expired' errors!\n\n"
            "⏳ Verification in progress...\n"
            "This may take **5-15 minutes**.\n\n"
            "_(Do not close this chat)_",
            parse_mode="Markdown"
        )
        
        try:
            from k12.cookie_verifier import verify_with_cookies
            
            result = await asyncio.to_thread(
                verify_with_cookies, 
                cookie_json=cookie_json,
                custom_email=custom_email
            )
            
            db.add_verification(
                user_id,
                "chatgpt_teacher_k12",
                "cookie_mode",
                "success" if result.get("success") else "failed",
                str(result),
            )
            
            teacher_info = result.get("teacher_info", {})
            profile_msg = ""
            if teacher_info:
                profile_msg = "\n\n📋 **Teacher Profile Used:**\n"
                profile_msg += f"• Name: `{teacher_info.get('name', 'N/A')}`\n"
                profile_msg += f"• Email: `{teacher_info.get('email', 'N/A')}`\n"
                profile_msg += f"• School: `{teacher_info.get('school', 'N/A')}`"
            
            if result.get("success"):
                result_msg = "✅ **Verification Successful!**\n\n"
                result_msg += "🎉 Teacher identity verified!\n"
                if result.get("redirect_url"):
                    result_msg += f"\n👉 **Click to claim:**\n{result['redirect_url']}"
                result_msg += profile_msg
                await processing_msg.edit_text(result_msg, parse_mode="Markdown")
            else:
                db.add_balance(user_id, VERIFY_COST)
                error_msg = f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
                error_msg += f"💰 Refunded {VERIFY_COST} points"
                error_msg += profile_msg
                await processing_msg.edit_text(error_msg, parse_mode="Markdown")
                
        except Exception as e:
            logger.error("Cookie verification error: %s", e)
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Cookie verification error: {str(e)}\n\n"
                f"Refunded {VERIFY_COST} points\n\n"
                f"💡 Make sure cookies are from SheerID page."
            )
    
    elif mode == "browser":
        # ========== BROWSER-BASED AUTO MODE ==========
        processing_msg = await update.message.reply_text(
            f"🎓 **ChatGPT Teacher K12 Verification** (Browser Mode)\n\n"
            f"{email_status}"
            f"Deducted {VERIFY_COST} points\n\n"
            "🌐 **Opening browser to get fresh link...**\n\n"
            "⏳ Full auto-verification in progress...\n"
            "This may take **5-15 minutes**.\n\n"
            "_(Do not close this chat)_",
            parse_mode="Markdown"
        )
        
        try:
            from k12.browser_verifier import verify_with_browser
            
            result = await asyncio.to_thread(
                verify_with_browser, 
                custom_email=custom_email, 
                headless=True
            )
            
            db.add_verification(
                user_id,
                "chatgpt_teacher_k12",
                "browser_auto",
                "success" if result.get("success") else "failed",
                str(result),
            )
            
            teacher_info = result.get("teacher_info", {})
            profile_msg = ""
            if teacher_info:
                profile_msg = "\n\n📋 **Teacher Profile Used:**\n"
                profile_msg += f"• Name: `{teacher_info.get('name', 'N/A')}`\n"
                profile_msg += f"• Email: `{teacher_info.get('email', 'N/A')}`\n"
                profile_msg += f"• School: `{teacher_info.get('school', 'N/A')}`"
            
            if result.get("success"):
                result_msg = "✅ **Verification Successful!**\n\n"
                result_msg += "🎉 Teacher identity verified!\n"
                if result.get("redirect_url"):
                    result_msg += f"\n👉 **Click to claim:**\n{result['redirect_url']}"
                result_msg += profile_msg
                await processing_msg.edit_text(result_msg, parse_mode="Markdown")
            else:
                db.add_balance(user_id, VERIFY_COST)
                error_msg = f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
                error_msg += f"💰 Refunded {VERIFY_COST} points"
                error_msg += profile_msg
                await processing_msg.edit_text(error_msg, parse_mode="Markdown")
                
        except Exception as e:
            logger.error("Browser verification error: %s", e)
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Browser verification error: {str(e)}\n\n"
                f"Refunded {VERIFY_COST} points\n\n"
                f"💡 _Try again or use legacy mode with a link._"
            )
    
    else:
        # ========== LEGACY LINK MODE ==========
        verification_id = K12Verifier.parse_verification_id(url)
        if not verification_id:
            db.add_balance(user_id, VERIFY_COST)
            await update.message.reply_text("Invalid SheerID link, please check and try again.")
            return

        # Show email status in processing message
        email_status = f"📧 Custom Email: `{custom_email}`\n" if custom_email else "📧 Using random teacher email\n"
        
        processing_msg = await update.message.reply_text(
            f"🎓 Starting ChatGPT Teacher K12 verification (Legacy Mode)...\n"
            f"Verification ID: `{verification_id}`\n"
            f"{email_status}"
            f"Deducted {VERIFY_COST} points\n\n"
            "⏳ **Full auto-verification in progress...**\n"
            "This may take **5-15 minutes**.\n\n"
            "_(Do not close this chat)_",
            parse_mode="Markdown"
        )

        try:
            verifier = K12Verifier(verification_id)
            result = await asyncio.to_thread(verifier.verify, auto_retry=True, custom_email=custom_email)

            db.add_verification(
                user_id,
                "chatgpt_teacher_k12",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )

            teacher_info = result.get("teacher_info", {})
            profile_msg = ""
            if teacher_info:
                profile_msg = "\n\n📋 **Teacher Profile Used:**\n"
                profile_msg += f"• Name: `{teacher_info.get('name', 'N/A')}`\n"
                profile_msg += f"• Email: `{teacher_info.get('email', 'N/A')}`\n"
                profile_msg += f"• School: `{teacher_info.get('school', 'N/A')}`"

            if result["success"]:
                result_msg = "✅ **Verification Successful!**\n\n"
                result_msg += "🎉 Teacher identity verified!\n"
                if result.get("redirect_url"):
                    result_msg += f"\n👉 **Click to claim:**\n{result['redirect_url']}"
                result_msg += profile_msg
                await processing_msg.edit_text(result_msg, parse_mode="Markdown")
            else:
                db.add_balance(user_id, VERIFY_COST)
                error_msg = f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
                error_msg += f"💰 Refunded {VERIFY_COST} points"
                error_msg += profile_msg
                await processing_msg.edit_text(error_msg, parse_mode="Markdown")
                
        except Exception as e:
            logger.error("Legacy verification error: %s", e)
            db.add_balance(user_id, VERIFY_COST)
            
            error_str = str(e)
            
            if "expired" in error_str.lower() or "404" in error_str:
                await processing_msg.edit_text(
                    f"❌ **Verification ID Expired**\n\n"
                    f"This link has already been used.\n\n"
                    f"💰 Refunded {VERIFY_COST} points\n\n"
                    f"💡 **Try auto-mode instead:**\n"
                    f"`/verify2` (no link needed)",
                    parse_mode="Markdown"
                )
            else:
                await processing_msg.edit_text(
                    f"❌ Error: {error_str}\n\n"
                    f"Refunded {VERIFY_COST} points"
                )


async def verify2_cookie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle cookie paste for K12 verification (2-step flow)
    
    Returns:
        True if message was handled (pending cookie verification exists)
        False if not handling this message
    """
    user_id = update.effective_user.id
    
    # Check if there's a pending cookie verification
    pending = context.user_data.get("pending_cookie_verify")
    if not pending:
        return False  # Not handling this message
    
    # Get cookie JSON from message
    cookie_json = update.message.text.strip()
    
    # Basic JSON validation
    if not cookie_json.startswith('[') or not cookie_json.endswith(']'):
        await update.message.reply_text(
            "❌ Invalid cookies format.\n\n"
            "Cookies phải là JSON array: `[{...}, {...}]`\n"
            "Hãy paste lại cookies từ EditThisCookie export.",
            parse_mode="Markdown"
        )
        return True  # Handled, but waiting for valid cookies
    
    # Clear pending state
    url = pending["url"]
    custom_email = pending.get("custom_email")
    fast_mode = pending.get("fast_mode", False)
    del context.user_data["pending_cookie_verify"]
    
    # Check balance
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            f"❌ Insufficient balance. Need {VERIFY_COST} points."
        )
        return True
    
    # Deduct balance
    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points.")
        return True
    
    # Start verification with real-time status updates
    email_status = f"📧 Custom Email: `{custom_email}`\n" if custom_email else "📧 Using random email\n"
    
    # Shared status log
    status_log = []
    
    def status_callback(step: str, message: str):
        """Callback to collect status updates"""
        status_log.append(f"{message}")
    
    mode_text = "⚡ FAST MODE" if fast_mode else "📄 Normal Mode"
    base_msg = (
        f"🎓 **ChatGPT Teacher K12** (Cookie Mode)\n\n"
        f"{email_status}"
        f"💰 Deducted {VERIFY_COST} points\n\n"
        f"🍪 {mode_text}\n\n"
    )
    
    processing_msg = await update.message.reply_text(
        base_msg + "⏳ Starting verification...",
        parse_mode="Markdown"
    )
    
    try:
        from k12.cookie_verifier import verify_with_cookies
        import concurrent.futures
        
        # Run verification in background thread
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = loop.run_in_executor(
                pool,
                lambda: verify_with_cookies(
                    cookie_json=cookie_json,
                    custom_email=custom_email,
                    status_callback=status_callback,
                    fast_mode=fast_mode
                )
            )
            
            # Poll for status updates while verification runs
            last_log_len = 0
            last_update_time = 0
            poll_count = 0
            max_poll_time = 900  # 15 min max
            start_time = asyncio.get_event_loop().time()
            
            while not future.done():
                await asyncio.sleep(3)  # Check every 3 seconds
                poll_count += 1
                
                # Timeout protection
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_poll_time:
                    logger.warning(f"Poll timeout after {elapsed}s")
                    break
                
                # Update message if new logs (with rate limit protection)
                if len(status_log) > last_log_len:
                    last_log_len = len(status_log)
                    
                    # Rate limit: only update every 5 seconds min
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_update_time >= 5:
                        last_update_time = current_time
                        # Show last 8 log entries - use plain text to avoid parsing errors
                        recent_logs = status_log[-8:]
                        log_text = "\n".join(recent_logs)
                        
                        # Simple base message without markdown
                        plain_msg = f"🔄 Cookie Verification\n\nProgress:\n{log_text}"
                        try:
                            await processing_msg.edit_text(plain_msg)
                        except Exception as e:
                            logger.debug(f"Failed to edit message: {e}")
            
            result = await future
        
        db.add_verification(
            user_id,
            "chatgpt_teacher_k12",
            url,
            "success" if result.get("success") else "failed",
            str(result),
        )
        
        teacher_info = result.get("teacher_info", {})
        profile_msg = ""
        if teacher_info:
            profile_msg = "\n\n📋 **Teacher Profile:**\n"
            profile_msg += f"• Name: {teacher_info.get('name', 'N/A')}\n"
            profile_msg += f"• Email: {teacher_info.get('email', 'N/A')}\n"
            profile_msg += f"• School: {teacher_info.get('school', 'N/A')}"
        
        # Send document image to Telegram for debugging
        doc_bytes = result.get("document_bytes")
        if doc_bytes:
            try:
                from io import BytesIO
                doc_file = BytesIO(doc_bytes)
                doc_file.name = "teacher_document.png"
                await update.message.reply_photo(
                    photo=doc_file,
                    caption="📄 Tài liệu đã upload lên SheerID"
                )
            except Exception as img_err:
                logger.warning(f"Failed to send doc image: {img_err}")
        
        if result.get("success"):
            result_msg = "✅ XÁC MINH THÀNH CÔNG!\n\n"
            result_msg += "🎉 Teacher identity verified!\n"
            if result.get("redirect_url"):
                result_msg += f"\n👉 Click to claim:\n{result['redirect_url']}"
            result_msg += profile_msg
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            
            # More detailed error message
            if result.get("rejected"):
                reasons = result.get("rejection_reasons", [])
                reason_text = ", ".join(reasons) if reasons else "Unknown"
                error_msg = f"❌ Bị từ chối: {reason_text}\n\n"
            elif result.get("timeout"):
                error_msg = "❌ Hết thời gian chờ duyệt\n\n"
            else:
                error_msg = f"❌ Lỗi: {result.get('message', 'Unknown')}\n\n"
            
            error_msg += f"💰 Đã hoàn {VERIFY_COST} points"
            error_msg += profile_msg
            await processing_msg.edit_text(error_msg)
            
    except Exception as e:
        logger.error("Cookie verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Lỗi: {str(e)}\n\n"
            f"Đã hoàn {VERIFY_COST} points"
        )
    
    return True  # Handled

async def verify3_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify3 command - Spotify Student"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify3", "Spotify Student")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # Parse verificationId
    verification_id = SpotifyVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Invalid SheerID link, please check and try again.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    processing_msg = await update.message.reply_text(
        f"🎵 Starting Spotify Student verification...\n"
        f"Deducted {VERIFY_COST} points\n\n"
        "📝 Generating student information...\n"
        "🎨 Generating student ID PNG...\n"
        "📤 Submitting document..."
    )

    # Use semaphore for concurrency control
    semaphore = get_verification_semaphore("spotify_student")

    try:
        async with semaphore:
            verifier = SpotifyVerifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "spotify_student",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ Spotify Student verification successful!\n\n"
            if result.get("pending"):
                result_msg += "✨ Document submitted, awaiting SheerID review\n"
                result_msg += "⏱️ Estimated review time: within minutes\n\n"
            if result.get("redirect_url"):
                result_msg += f"🔗 Redirect link:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
                f"Refunded {VERIFY_COST} points"
            )
    except Exception as e:
        logger.error("Spotify verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Error during processing: {str(e)}\n\n"
            f"Refunded {VERIFY_COST} points"
        )


async def verify4_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify4 command - Bolt.new Teacher (auto get code version)"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify4", "Bolt.new Teacher")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # Parse externalUserId or verificationId
    external_user_id = BoltnewVerifier.parse_external_user_id(url)
    verification_id = BoltnewVerifier.parse_verification_id(url)

    if not external_user_id and not verification_id:
        await update.message.reply_text("Invalid SheerID link, please check and try again.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    processing_msg = await update.message.reply_text(
        f"🚀 Starting Bolt.new Teacher verification...\n"
        f"Deducted {VERIFY_COST} points\n\n"
        "📤 Submitting document..."
    )

    # Use semaphore for concurrency control
    semaphore = get_verification_semaphore("bolt_teacher")

    try:
        async with semaphore:
            # Step 1: Submit document
            verifier = BoltnewVerifier(url, verification_id=verification_id)
            result = await asyncio.to_thread(verifier.verify)

        if not result.get("success"):
            # Submission failed, refund
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Document submission failed: {result.get('message', 'Unknown error')}\n\n"
                f"Refunded {VERIFY_COST} points"
            )
            return

        vid = result.get("verification_id", "")
        if not vid:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Verification ID not obtained\n\n"
                f"Refunded {VERIFY_COST} points"
            )
            return

        # Update message
        await processing_msg.edit_text(
            f"✅ Document submitted!\n"
            f"📋 Verification ID: `{vid}`\n\n"
            f"🔍 Automatically retrieving verification code...\n"
            f"(Maximum wait 20 seconds)"
        )

        # Step 2: Auto get verification code (max 20 seconds)
        code = await _auto_get_reward_code(vid, max_wait=20, interval=5)

        if code:
            # Successfully obtained
            result_msg = (
                f"🎉 Verification successful!\n\n"
                f"✅ Document submitted\n"
                f"✅ Review passed\n"
                f"✅ Verification code obtained\n\n"
                f"🎁 Verification code: `{code}`\n"
            )
            if result.get("redirect_url"):
                result_msg += f"\n🔗 Redirect link:\n{result['redirect_url']}"

            await processing_msg.edit_text(result_msg)

            # Save success record
            db.add_verification(
                user_id,
                "bolt_teacher",
                url,
                "success",
                f"Code: {code}",
                vid
            )
        else:
            # Not obtained within 20 seconds, let user query later
            await processing_msg.edit_text(
                f"✅ Document submitted successfully!\n\n"
                f"⏳ Verification code not yet generated (review may take 1-5 minutes)\n\n"
                f"📋 Verification ID: `{vid}`\n\n"
                f"💡 Please query later using:\n"
                f"`/getV4Code {vid}`\n\n"
                f"Note: Points already consumed, no additional fee for later query"
            )

            # Save pending record
            db.add_verification(
                user_id,
                "bolt_teacher",
                url,
                "pending",
                "Waiting for review",
                vid
            )

    except Exception as e:
        logger.error("Bolt.new verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Error during processing: {str(e)}\n\n"
            f"Refunded {VERIFY_COST} points"
        )


async def _auto_get_reward_code(
    verification_id: str,
    max_wait: int = 20,
    interval: int = 5
) -> Optional[str]:
    """Auto get verification code (lightweight polling, doesn't affect concurrency)

    Args:
        verification_id: Verification ID
        max_wait: Maximum wait time (seconds)
        interval: Polling interval (seconds)

    Returns:
        str: Verification code, None if failed to obtain
    """
    import time
    start_time = time.time()
    attempts = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            elapsed = int(time.time() - start_time)
            attempts += 1

            # Check timeout
            if elapsed >= max_wait:
                logger.info(f"Auto get code timeout ({elapsed}s), letting user query manually")
                return None

            try:
                # Query verification status
                response = await client.get(
                    f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
                )

                if response.status_code == 200:
                    data = response.json()
                    current_step = data.get("currentStep")

                    if current_step == "success":
                        # Get verification code
                        code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
                        if code:
                            logger.info(f"✅ Auto get code success: {code} (took {elapsed}s)")
                            return code
                    elif current_step == "error":
                        # Review failed
                        logger.warning(f"Review failed: {data.get('errorIds', [])}")
                        return None
                    # else: pending, continue waiting

                # Wait for next poll
                await asyncio.sleep(interval)

            except Exception as e:
                logger.warning(f"Error querying verification code: {e}")
                await asyncio.sleep(interval)

    return None


async def verify5_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify5 command - YouTube Student Premium"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify5", "YouTube Student Premium")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # Parse verificationId
    verification_id = YouTubeVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Invalid SheerID link, please check and try again.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    processing_msg = await update.message.reply_text(
        f"📺 Starting YouTube Student Premium verification...\n"
        f"Deducted {VERIFY_COST} points\n\n"
        "📝 Generating student information...\n"
        "🎨 Generating student ID PNG...\n"
        "📤 Submitting document..."
    )

    # Use semaphore for concurrency control
    semaphore = get_verification_semaphore("youtube_student")

    try:
        async with semaphore:
            verifier = YouTubeVerifier(verification_id)
            result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "youtube_student",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ YouTube Student Premium verification successful!\n\n"
            if result.get("pending"):
                result_msg += "✨ Document submitted, awaiting SheerID review\n"
                result_msg += "⏱️ Estimated review time: within minutes\n\n"
            if result.get("redirect_url"):
                result_msg += f"🔗 Redirect link:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Verification failed: {result.get('message', 'Unknown error')}\n\n"
                f"Refunded {VERIFY_COST} points"
            )
    except Exception as e:
        logger.error("YouTube verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Error during processing: {str(e)}\n\n"
            f"Refunded {VERIFY_COST} points"
        )


async def getV4Code_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /getV4Code command - Get Bolt.new Teacher verification code"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    # Check if verification_id is provided
    if not context.args:
        await update.message.reply_text(
            "Usage: /getV4Code <verification_id>\n\n"
            "Example: /getV4Code 6929436b50d7dc18638890d0\n\n"
            "The verification_id is returned when you use the /verify4 command."
        )
        return

    verification_id = context.args[0].strip()

    processing_msg = await update.message.reply_text(
        "🔍 Querying verification code, please wait..."
    )

    try:
        # Query SheerID API for verification code
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
            )

            if response.status_code != 200:
                await processing_msg.edit_text(
                    f"❌ Query failed, status code: {response.status_code}\n\n"
                    "Please try again later or contact admin."
                )
                return

            data = response.json()
            current_step = data.get("currentStep")
            reward_code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
            redirect_url = data.get("redirectUrl")

            if current_step == "success" and reward_code:
                result_msg = "✅ Verification successful!\n\n"
                result_msg += f"🎉 Verification code: `{reward_code}`\n\n"
                if redirect_url:
                    result_msg += f"Redirect link:\n{redirect_url}"
                await processing_msg.edit_text(result_msg)
            elif current_step == "pending":
                await processing_msg.edit_text(
                    "⏳ Verification is still under review, please try again later.\n\n"
                    "Usually takes 1-5 minutes, please be patient."
                )
            elif current_step == "error":
                error_ids = data.get("errorIds", [])
                await processing_msg.edit_text(
                    f"❌ Verification failed\n\n"
                    f"Error: {', '.join(error_ids) if error_ids else 'Unknown error'}"
                )
            else:
                await processing_msg.edit_text(
                    f"⚠️ Current status: {current_step}\n\n"
                    "Verification code not yet generated, please try again later."
                )

    except Exception as e:
        logger.error("Failed to get Bolt.new verification code: %s", e)
        await processing_msg.edit_text(
            f"❌ Error during query: {str(e)}\n\n"
            "Please try again later or contact admin."
        )


async def verify6_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /verify6 command - ChatGPT Military (Veteran) Verification"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            "📋 **Usage:** `/verify6 <sheerid_link>`\n\n"
            "**Example:**\n"
            "`/verify6 https://services.sheerid.com/verify/...`\n\n"
            "I will ask for your email in the next step.",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    
    # Check if email is provided as second argument
    if len(context.args) >= 2:
        user_email = context.args[1]
        # Proceed directly with verification
        await _execute_military_verification(update, context, db, url, user_email)
        return
    
    # Validate verification link first
    verification_id = MilitaryVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("❌ Invalid SheerID link, please check and try again.")
        return
    
    # Check balance before asking for email
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return
    
    # Store pending verification in user_data
    context.user_data["pending_military_verification"] = {
        "url": url,
        "verification_id": verification_id
    }
    
    # Ask for email
    await update.message.reply_text(
        "📧 **Please enter your email address:**\n\n"
        "This email will receive the SheerID verification link.\n"
        "Simply reply with your email (e.g., `your@email.com`)\n\n"
        "⚠️ Use a real email you can access to complete verification!",
        parse_mode="Markdown"
    )


async def verify6_email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle email reply for military verification
    
    Returns:
        True if message was handled (pending verification exists)
        False if not handling this message
    """
    user_id = update.effective_user.id
    
    # Check if there's a pending military verification
    pending = context.user_data.get("pending_military_verification")
    if not pending:
        return False  # Not handling this message
    
    # Get email from message
    user_email = update.message.text.strip()
    
    # Basic email validation
    if "@" not in user_email or "." not in user_email:
        await update.message.reply_text(
            "❌ Invalid email format. Please enter a valid email address.\n"
            "Example: `your@email.com`",
            parse_mode="Markdown"
        )
        return True  # Handled, but waiting for valid email
    
    # Clear pending state
    url = pending["url"]
    del context.user_data["pending_military_verification"]
    
    # Execute verification
    await _execute_military_verification(update, context, db, url, user_email)
    return True  # Handled


async def _execute_military_verification(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    db: Database,
    url: str,
    user_email: str
):
    """Execute the actual military verification process"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    verification_id = MilitaryVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("❌ Invalid SheerID link, please check and try again.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Failed to deduct points, please try again later.")
        return

    processing_msg = await update.message.reply_text(
        f"🎖️ Starting ChatGPT Military (Veteran) verification...\n"
        f"Verification ID: `{verification_id}`\n"
        f"Email: `{user_email}`\n"
        f"Deducted {VERIFY_COST} points\n\n"
        "⏳ Please wait, this may take 20-30 seconds...\n"
        "_(Adding human-like delays to avoid bot detection)_",
        parse_mode="Markdown"
    )

    try:
        verifier = MilitaryVerifier(verification_id, email=user_email)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "chatgpt_military",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            current_step = result.get("current_step", "")
            
            # Get veteran info from debug data
            debug_info = result.get("debug_info", {})
            veteran_info = debug_info.get("veteran_info", {})
            
            # Build veteran profile section
            profile_msg = ""
            if veteran_info:
                profile_msg = "\n📋 **Veteran Profile Used:**\n"
                profile_msg += f"• Name: `{veteran_info.get('name', 'N/A')}`\n"
                profile_msg += f"• Birth Date: `{veteran_info.get('birth_date', 'N/A')}`\n"
                profile_msg += f"• Branch: `{veteran_info.get('branch', 'N/A')}`\n"
                profile_msg += f"• Discharge Date: `{veteran_info.get('discharge_date', 'N/A')}`\n"
            
            # Handle emailLoop status
            if current_step == "emailLoop":
                result_msg = "✅ Military verification submitted!\n\n"
                result_msg += f"📧 **Email verification required!**\n"
                result_msg += f"Check your inbox: `{user_email}`\n\n"
                result_msg += "🔗 Click the verification link in the email from SheerID to complete verification.\n"
                result_msg += "\n⚠️ If you don't see the email, check your spam folder."
                result_msg += profile_msg
            else:
                result_msg = "✅ Military verification successful!\n\n"
                if result.get("pending"):
                    result_msg += f"⏳ {result.get('message', 'Submitted, awaiting review')}\n"
                    result_msg += f"📌 Status: `{current_step}`\n"
                if result.get("reward_code"):
                    result_msg += f"🎉 Verification code: `{result['reward_code']}`\n"
                if result.get("redirect_url"):
                    result_msg += f"\n👉 Click to continue with OpenAI:\n{result['redirect_url']}"
                result_msg += profile_msg
            
            await processing_msg.edit_text(result_msg, parse_mode="Markdown")
        else:
            db.add_balance(user_id, VERIFY_COST)
            
            # Build detailed error message for debugging
            error_msg = f"❌ Military verification failed\n\n"
            error_msg += f"📋 Error: {result.get('message', 'Unknown error')}\n"
            
            if result.get('step'):
                error_msg += f"Step: {result.get('step')}\n"
            
            if result.get('error_ids'):
                error_msg += f"Error IDs: {', '.join(result.get('error_ids'))}\n"
            
            # Add debug info
            debug_info = result.get('debug_info', {})
            if debug_info.get('veteran_info'):
                vi = debug_info['veteran_info']
                error_msg += f"\n📋 Profile used:\n"
                error_msg += f"• Name: {vi.get('name', 'N/A')}\n"
                error_msg += f"• Birth: {vi.get('birth_date', 'N/A')}\n"
                error_msg += f"• Branch: {vi.get('branch', 'N/A')}\n"
                error_msg += f"• Discharge: {vi.get('discharge_date', 'N/A')}\n"
            
            error_msg += f"\n💰 Refunded {VERIFY_COST} points"
            
            await processing_msg.edit_text(error_msg)

    except Exception as e:
        logger.error("Military verification error: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Verification error: {str(e)}\n\n"
            f"Refunded {VERIFY_COST} points\n\n"
            "Please check your link and try again."
        )


async def checkStatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle /checkStatus command - Check SheerID verification status"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("You have been blocked and cannot use this feature.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    if not context.args:
        await update.message.reply_text(
            "📋 **Usage:** `/checkStatus <verificationId>`\n\n"
            "**Example:**\n"
            "`/checkStatus 6940e60f4f4e4d71f2a4ab9d`\n\n"
            "The verification ID is from your SheerID link.",
            parse_mode="Markdown"
        )
        return

    verification_id = context.args[0]
    
    # Clean up verification ID if user pastes full URL
    if "verificationId=" in verification_id:
        import re
        match = re.search(r'verificationId=([a-f0-9]+)', verification_id, re.IGNORECASE)
        if match:
            verification_id = match.group(1)

    processing_msg = await update.message.reply_text(
        f"🔄 Checking verification status...\n"
        f"ID: `{verification_id}`",
        parse_mode="Markdown"
    )

    try:
        # Call SheerID API to check status
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
            )
            
            if response.status_code == 404:
                await processing_msg.edit_text(
                    f"❌ Verification not found!\n\n"
                    f"ID: `{verification_id}`\n\n"
                    "This verification ID may have expired or never existed.",
                    parse_mode="Markdown"
                )
                return
            
            data = response.json()
        
        current_step = data.get("currentStep", "unknown")
        segment = data.get("segment", "unknown")
        redirect_url = data.get("redirectUrl")
        reward_code = data.get("rewardCode")
        error_ids = data.get("errorIds", [])
        
        # Build status message
        if current_step == "success":
            result_msg = "✅ **Verification APPROVED!**\n\n"
            result_msg += f"📋 Type: `{segment}`\n"
            if reward_code:
                result_msg += f"🎉 Reward Code: `{reward_code}`\n"
            if redirect_url:
                result_msg += f"\n👉 **Click to claim:**\n{redirect_url}"
            else:
                result_msg += "\n✨ Your discount should now be active!"
                
        elif current_step == "pending":
            result_msg = "⏳ **Status: PENDING**\n\n"
            result_msg += f"📋 Type: `{segment}`\n"
            result_msg += "SheerID is still reviewing your documents.\n"
            result_msg += "Please check again later (usually 1-24 hours)."
            
        elif current_step == "rejected" or current_step == "error":
            result_msg = "❌ **Status: REJECTED**\n\n"
            result_msg += f"📋 Type: `{segment}`\n"
            if error_ids:
                result_msg += f"Reason: `{', '.join(error_ids)}`\n"
            result_msg += "\nYour verification was not approved."
            
        elif current_step == "docUpload":
            result_msg = "📄 **Status: Document Upload Required**\n\n"
            result_msg += f"📋 Type: `{segment}`\n"
            result_msg += "Additional documents may be needed."
            
        else:
            result_msg = f"📊 **Status: {current_step.upper()}**\n\n"
            result_msg += f"📋 Type: `{segment}`\n"
            if redirect_url:
                result_msg += f"\n👉 Link: {redirect_url}"
        
        await processing_msg.edit_text(result_msg, parse_mode="Markdown")

    except Exception as e:
        logger.error("Check status error: %s", e)
        await processing_msg.edit_text(
            f"❌ Error checking status: {str(e)}\n\n"
            "Please try again later."
        )
