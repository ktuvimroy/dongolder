"""Signal message formatting for Telegram.

This module provides functions to format RawSignal objects
into readable Telegram messages with emoji indicators.
"""

from gold_signal_bot.analysis.models import RawSignal


# Emoji indicators
EMOJI_BUY = "🟢"
EMOJI_SELL = "🔴"
EMOJI_ENTRY = "📍"
EMOJI_STOP_LOSS = "🛑"
EMOJI_TARGET = "🎯"
EMOJI_CHART = "📊"
EMOJI_REASON = "💡"
EMOJI_RISK = "⚖️"


def format_signal(signal: RawSignal, html: bool = True) -> str:
    """Format a RawSignal into a Telegram message.
    
    Args:
        signal: The raw signal to format.
        html: If True, use HTML formatting; otherwise plain text.
    
    Returns:
        Formatted message string ready for Telegram.
    """
    direction_emoji = EMOJI_BUY if signal.direction == "BUY" else EMOJI_SELL
    direction_text = "BUY" if signal.direction == "BUY" else "SELL"
    
    if html:
        return _format_html(signal, direction_emoji, direction_text)
    return _format_plain(signal, direction_emoji, direction_text)


def _format_html(signal: RawSignal, emoji: str, direction: str) -> str:
    """Format signal as HTML message."""
    # Header
    lines = [
        f"{emoji} <b>GOLD {direction} SIGNAL</b> {emoji}",
        f"<i>{signal.timeframe} timeframe</i>",
        "",
    ]
    
    # Price levels
    lines.append(f"{EMOJI_ENTRY} <b>Entry:</b> ${signal.entry_price:.2f}")
    lines.append(f"{EMOJI_STOP_LOSS} <b>Stop Loss:</b> ${signal.stop_loss:.2f}")
    lines.append(f"{EMOJI_TARGET} <b>Take Profit 1:</b> ${signal.take_profit_1:.2f}")
    
    if signal.take_profit_2 is not None:
        lines.append(f"{EMOJI_TARGET} <b>Take Profit 2:</b> ${signal.take_profit_2:.2f}")
    
    # Risk/Reward ratio
    lines.append("")
    rr = signal.risk_reward_ratio
    lines.append(f"{EMOJI_RISK} <b>Risk/Reward:</b> 1:{rr:.2f}")
    
    # Reasoning section
    if signal.reasoning:
        lines.append("")
        lines.append(f"{EMOJI_REASON} <b>Analysis:</b>")
        for reason in signal.reasoning[:5]:  # Limit to 5 reasons
            # Truncate long reasons
            display_reason = reason if len(reason) <= 100 else reason[:97] + "..."
            lines.append(f"• {display_reason}")
    
    # Support/Resistance info
    if signal.nearby_support or signal.nearby_resistance:
        lines.append("")
        lines.append(f"{EMOJI_CHART} <b>Key Levels:</b>")
        if signal.nearby_support:
            lines.append(f"• Support: ${signal.nearby_support.price:.2f}")
        if signal.nearby_resistance:
            lines.append(f"• Resistance: ${signal.nearby_resistance.price:.2f}")
    
    # Timestamp footer
    lines.append("")
    lines.append(f"<i>Generated: {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}</i>")
    
    return "\n".join(lines)


def _format_plain(signal: RawSignal, emoji: str, direction: str) -> str:
    """Format signal as plain text message."""
    # Header
    lines = [
        f"{emoji} GOLD {direction} SIGNAL {emoji}",
        f"{signal.timeframe} timeframe",
        "",
    ]
    
    # Price levels
    lines.append(f"{EMOJI_ENTRY} Entry: ${signal.entry_price:.2f}")
    lines.append(f"{EMOJI_STOP_LOSS} Stop Loss: ${signal.stop_loss:.2f}")
    lines.append(f"{EMOJI_TARGET} Take Profit 1: ${signal.take_profit_1:.2f}")
    
    if signal.take_profit_2 is not None:
        lines.append(f"{EMOJI_TARGET} Take Profit 2: ${signal.take_profit_2:.2f}")
    
    # Risk/Reward ratio
    lines.append("")
    rr = signal.risk_reward_ratio
    lines.append(f"{EMOJI_RISK} Risk/Reward: 1:{rr:.2f}")
    
    # Reasoning section
    if signal.reasoning:
        lines.append("")
        lines.append(f"{EMOJI_REASON} Analysis:")
        for reason in signal.reasoning[:5]:
            display_reason = reason if len(reason) <= 100 else reason[:97] + "..."
            lines.append(f"• {display_reason}")
    
    # Support/Resistance info
    if signal.nearby_support or signal.nearby_resistance:
        lines.append("")
        lines.append(f"{EMOJI_CHART} Key Levels:")
        if signal.nearby_support:
            lines.append(f"• Support: ${signal.nearby_support.price:.2f}")
        if signal.nearby_resistance:
            lines.append(f"• Resistance: ${signal.nearby_resistance.price:.2f}")
    
    # Timestamp footer
    lines.append("")
    lines.append(f"Generated: {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
    
    return "\n".join(lines)


class SignalFormatter:
    """Stateful signal formatter with configuration.
    
    This class provides a configurable formatter that can be
    reused across multiple signals with consistent settings.
    """
    
    def __init__(self, html: bool = True, max_reasons: int = 5) -> None:
        """Initialize the formatter.
        
        Args:
            html: Whether to use HTML formatting.
            max_reasons: Maximum number of reasoning lines to include.
        """
        self.html = html
        self.max_reasons = max_reasons
    
    def format(self, signal: RawSignal) -> str:
        """Format a signal using configured settings.
        
        Args:
            signal: The raw signal to format.
        
        Returns:
            Formatted message string.
        """
        return format_signal(signal, html=self.html)
