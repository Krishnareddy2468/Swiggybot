import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
)
from app.services.gemini_agent import gemini_agent
from app.services.order_service import order_service

logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.app = None
        self.bot = None
        self._running = False

        if not self.token or self.token == "your_telegram_bot_token_here":
            logger.warning("TELEGRAM_BOT_TOKEN not configured - bot won't start")
            return

        self.bot = Bot(token=self.token)

    async def start(self):
        if not self.token or self.token == "your_telegram_bot_token_here":
            logger.warning("Skipping telegram bot - no valid token set")
            return

        try:
            self.app = Application.builder().token(self.token).build()

            # register all the handlers
            self.app.add_handler(CommandHandler("start", self._handle_start))
            self.app.add_handler(CommandHandler("help", self._handle_help))
            self.app.add_handler(CommandHandler("menu", self._handle_menu))
            self.app.add_handler(CommandHandler("cart", self._handle_cart))
            self.app.add_handler(CommandHandler("status", self._handle_status))
            self.app.add_handler(CommandHandler("reset", self._handle_reset))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            self.app.add_handler(MessageHandler(filters.LOCATION, self._handle_location))

            self._running = True
            logger.info("Telegram bot starting polling...")
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot is running")

        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            self._running = False

    async def stop(self):
        if self.app and self._running:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
                self._running = False
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")

    async def send_message(self, user_id: str, text: str):
        """send a message to a user - used for order status notifications"""
        if not self.bot:
            return
        try:
            max_len = 4000
            if len(text) > max_len:
                # telegram has a character limit so we split long messages
                parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
                for part in parts:
                    await self.bot.send_message(chat_id=int(user_id), text=part, parse_mode="Markdown")
            else:
                await self.bot.send_message(chat_id=int(user_id), text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            # sometimes markdown parsing fails, retry as plain text
            try:
                await self.bot.send_message(chat_id=int(user_id), text=text)
            except Exception as e2:
                logger.error(f"Even plain text failed: {e2}")

    # -- command handlers --

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        user_name = user.first_name or user.username or ""
        response = await gemini_agent.process_message(user_id, "hi", user_name)
        await self._send_response(update, response)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = await gemini_agent.process_message(user_id, "help")
        await self._send_response(update, response)

    async def _handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = await gemini_agent.process_message(user_id, "show menu")
        await self._send_response(update, response)

    async def _handle_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = await gemini_agent.process_message(user_id, "show cart")
        await self._send_response(update, response)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = await gemini_agent.process_message(user_id, "order status")
        await self._send_response(update, response)

    async def _handle_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = await gemini_agent.process_message(user_id, "start over")
        await self._send_response(update, response)

    # -- message handlers --

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        user_name = user.first_name or user.username or ""
        message = update.message.text

        logger.info(f"[{user_name}] ({user_id}): {message}")
        await update.message.chat.send_action("typing")

        response = await gemini_agent.process_message(user_id, message, user_name)
        logger.info(f"Response to {user_name}: {response[:80]}...")
        await self._send_response(update, response)

        # if an order was just placed, kick off the status simulation
        from app.services.session_service import session_service
        session = session_service.get_session(user_id)
        if session.current_order_id:
            order = order_service.get_order(session.current_order_id)
            if order and order.status.value == "confirmed":
                asyncio.create_task(
                    order_service.simulate_order_progress(
                        session.current_order_id,
                        send_update_callback=self._send_order_update,
                    )
                )

    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        loc = update.message.location

        # we don't have reverse geocoding so just use coords + hardcoded area
        address = f"Location: {loc.latitude:.4f}, {loc.longitude:.4f}\n(Near Koramangala, Bangalore)"
        response = await gemini_agent.process_message(user_id, address)
        await self._send_response(update, response)

    # -- utils --

    async def _send_response(self, update: Update, text: str):
        """try to send with markdown first, fall back to plain if it fails"""
        try:
            max_len = 4000
            if len(text) > max_len:
                parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
                for part in parts:
                    try:
                        await update.message.reply_text(part, parse_mode="Markdown")
                    except Exception:
                        await update.message.reply_text(part)
            else:
                try:
                    await update.message.reply_text(text, parse_mode="Markdown")
                except Exception:
                    await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try again!")

    async def _send_order_update(self, user_id: str, message: str):
        await self.send_message(user_id, message)


telegram_bot = TelegramBotService()
