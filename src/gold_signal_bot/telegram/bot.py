"""Telegram bot client for sending messages.

This module provides an async Telegram bot wrapper using python-telegram-bot.
"""

from telegram import Bot
from telegram.constants import ParseMode

from gold_signal_bot.analysis.models import RawSignal
from gold_signal_bot.config import Settings
from gold_signal_bot.telegram.formatter import format_signal


class TelegramBot:
    """Telegram bot client for sending trading signals.
    
    This class wraps the python-telegram-bot library to provide
    a simple interface for sending formatted signal messages.
    
    Attributes:
        bot: The underlying Telegram Bot instance.
        chat_id: Target chat/channel ID for messages.
        parse_mode: Message parse mode (HTML or Markdown).
    """
    
    def __init__(self, settings: Settings) -> None:
        """Initialize the Telegram bot.
        
        Args:
            settings: Application settings containing bot token and chat ID.
        
        Raises:
            ValueError: If bot token or chat ID is not configured.
        """
        if not settings.telegram_bot_token:
            raise ValueError("telegram_bot_token is required")
        if not settings.telegram_chat_id:
            raise ValueError("telegram_chat_id is required")
        
        self.bot = Bot(token=settings.telegram_bot_token)
        self.chat_id = settings.telegram_chat_id
        self.parse_mode = (
            ParseMode.HTML 
            if settings.telegram_parse_mode.upper() == "HTML" 
            else ParseMode.MARKDOWN_V2
        )
    
    async def send_message(self, text: str, disable_preview: bool = True) -> bool:
        """Send a text message to the configured chat.
        
        Args:
            text: The message text to send.
            disable_preview: Whether to disable link previews.
        
        Returns:
            True if message was sent successfully, False otherwise.
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=self.parse_mode,
                disable_web_page_preview=disable_preview,
            )
            return True
        except Exception:
            # Log error in production; for now just return failure
            return False
    
    async def send_signal(self, signal: RawSignal) -> bool:
        """Format and send a trading signal.
        
        Args:
            signal: The raw signal to format and send.
        
        Returns:
            True if signal was sent successfully, False otherwise.
        """
        message = format_signal(signal)
        return await self.send_message(message)
    
    async def close(self) -> None:
        """Close the bot session and release resources."""
        await self.bot.shutdown()
