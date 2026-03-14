"""Telegram integration module for signal delivery.

This module provides the bot interface and message formatting
for delivering trading signals via Telegram.
"""

from gold_signal_bot.telegram.bot import TelegramBot
from gold_signal_bot.telegram.formatter import SignalFormatter, format_signal

__all__ = ["TelegramBot", "SignalFormatter", "format_signal"]
