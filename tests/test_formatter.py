"""Tests for Telegram signal formatter."""

from datetime import datetime

import pytest

from gold_signal_bot.analysis.models import (
    PriceLevel,
    RawSignal,
    TechnicalSnapshot,
    RSIResult,
    SignalDirection,
)
from gold_signal_bot.telegram.formatter import (
    format_signal,
    SignalFormatter,
    EMOJI_BUY,
    EMOJI_SELL,
)


def create_test_signal(
    direction: str = "BUY",
    entry: float = 2000.00,
    stop_loss: float = 1990.00,
    take_profit_1: float = 2020.00,
    take_profit_2: float | None = 2040.00,
    reasoning: list[str] | None = None,
    support: PriceLevel | None = None,
    resistance: PriceLevel | None = None,
    confidence: float = 0.75,
) -> RawSignal:
    """Create a test signal with default values."""
    if reasoning is None:
        reasoning = ["RSI oversold at 28", "Price above EMA 21"]
    
    snapshot = TechnicalSnapshot(
        timestamp=datetime(2026, 3, 14, 12, 0),
        rsi=RSIResult(value=28.0, signal=SignalDirection.BULLISH),
        macd=None,
        ema=None,
        bollinger=None,
    )
    
    return RawSignal(
        timestamp=datetime(2026, 3, 14, 12, 0),
        direction=direction,
        timeframe="1H",
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        reasoning=reasoning,
        indicators=snapshot,
        nearby_support=support,
        nearby_resistance=resistance,
        confidence=confidence,
    )


class TestFormatSignal:
    """Tests for format_signal function."""
    
    def test_buy_signal_contains_correct_emoji(self) -> None:
        """BUY signals should use green emoji."""
        signal = create_test_signal(direction="BUY")
        result = format_signal(signal)
        
        assert EMOJI_BUY in result
        assert "BUY" in result
    
    def test_sell_signal_contains_correct_emoji(self) -> None:
        """SELL signals should use red emoji."""
        signal = create_test_signal(direction="SELL")
        result = format_signal(signal)
        
        assert EMOJI_SELL in result
        assert "SELL" in result
    
    def test_entry_price_formatted(self) -> None:
        """Entry price should be formatted with $ and 2 decimals."""
        signal = create_test_signal(entry=2000.50)
        result = format_signal(signal)
        
        assert "$2000.50" in result
        assert "Entry" in result
    
    def test_stop_loss_formatted(self) -> None:
        """Stop loss should be formatted with $ and 2 decimals."""
        signal = create_test_signal(stop_loss=1995.75)
        result = format_signal(signal)
        
        assert "$1995.75" in result
        assert "Stop Loss" in result
    
    def test_take_profit_levels_formatted(self) -> None:
        """Both TP levels should be included when present."""
        signal = create_test_signal(take_profit_1=2020.00, take_profit_2=2040.00)
        result = format_signal(signal)
        
        assert "$2020.00" in result
        assert "$2040.00" in result
        assert "Take Profit" in result
    
    def test_optional_take_profit_2_excluded_when_none(self) -> None:
        """TP2 should not appear when it's None."""
        signal = create_test_signal(take_profit_2=None)
        result = format_signal(signal)
        
        # Should have TP1 but message should only mention it once
        assert result.count("Take Profit") == 1
    
    def test_reasoning_included(self) -> None:
        """Reasoning lines should appear in output."""
        reasons = ["RSI oversold at 28", "MACD bullish crossover"]
        signal = create_test_signal(reasoning=reasons)
        result = format_signal(signal)
        
        assert "RSI oversold at 28" in result
        assert "MACD bullish crossover" in result
    
    def test_empty_reasoning_handled(self) -> None:
        """Empty reasoning list should not cause errors."""
        signal = create_test_signal(reasoning=[])
        result = format_signal(signal)
        
        # Should still produce valid output
        assert "GOLD" in result
        assert "Entry" in result
    
    def test_long_reasoning_truncated(self) -> None:
        """Reasoning lines over 100 chars should be truncated."""
        long_reason = "A" * 150
        signal = create_test_signal(reasoning=[long_reason])
        result = format_signal(signal)
        
        # Should be truncated with ellipsis
        assert "..." in result
        assert "A" * 150 not in result
        assert "A" * 97 in result
    
    def test_large_prices_formatted_correctly(self) -> None:
        """Large price values should format correctly."""
        signal = create_test_signal(
            entry=12345.67,
            stop_loss=12300.00,
            take_profit_1=12500.00,
        )
        result = format_signal(signal)
        
        assert "$12345.67" in result
        assert "$12300.00" in result
        assert "$12500.00" in result
    
    def test_risk_reward_ratio_included(self) -> None:
        """Risk/Reward ratio should be calculated and displayed."""
        # Entry 2000, SL 1990, TP1 2030 -> Risk 10, Reward 30 -> R:R = 1:3
        signal = create_test_signal(
            entry=2000.00,
            stop_loss=1990.00,
            take_profit_1=2030.00,
        )
        result = format_signal(signal)
        
        assert "Risk/Reward" in result
        assert "1:3.00" in result
    
    def test_support_resistance_levels_shown(self) -> None:
        """Support and resistance levels should appear when present."""
        support = PriceLevel(price=1980.00, level_type="support", strength=3)
        resistance = PriceLevel(price=2050.00, level_type="resistance", strength=2)
        
        signal = create_test_signal(support=support, resistance=resistance)
        result = format_signal(signal)
        
        assert "$1980.00" in result
        assert "$2050.00" in result
        assert "Support" in result
        assert "Resistance" in result
    
    def test_html_formatting_applied(self) -> None:
        """HTML mode should include HTML tags."""
        signal = create_test_signal()
        result = format_signal(signal, html=True)
        
        assert "<b>" in result
        assert "</b>" in result
    
    def test_plain_text_no_html_tags(self) -> None:
        """Plain text mode should not include HTML tags."""
        signal = create_test_signal()
        result = format_signal(signal, html=False)
        
        assert "<b>" not in result
        assert "</b>" not in result
    
    def test_timestamp_included(self) -> None:
        """Timestamp should be included in footer."""
        signal = create_test_signal()
        result = format_signal(signal)
        
        assert "2026-03-14" in result
        assert "12:00" in result
    
    def test_confidence_display_medium_tier(self) -> None:
        """Confidence should be displayed with percentage and tier."""
        signal = create_test_signal(confidence=0.75)
        result = format_signal(signal)
        
        assert "75%" in result
        assert "MEDIUM" in result
        assert "Confidence" in result
        # Confidence bar should appear (75% = 7 filled, 3 empty)
        assert "███████░░░" in result
    
    def test_confidence_display_high_tier(self) -> None:
        """High confidence (>=80%) should show HIGH tier."""
        signal = create_test_signal(confidence=0.85)
        result = format_signal(signal)
        
        assert "85%" in result
        assert "HIGH" in result
        # Confidence bar should appear (85% = 8 filled, 2 empty)
        assert "████████░░" in result
    
    def test_confidence_display_low_tier(self) -> None:
        """Low confidence (<60%) should show LOW tier."""
        signal = create_test_signal(confidence=0.45)
        result = format_signal(signal)
        
        assert "45%" in result
        assert "LOW" in result
        # Confidence bar should appear (45% = 4 filled, 6 empty)
        assert "████░░░░░░" in result
    
    def test_confidence_bar_full(self) -> None:
        """100% confidence should show full bar."""
        signal = create_test_signal(confidence=1.0)
        result = format_signal(signal)
        
        assert "100%" in result
        assert "██████████" in result
    
    def test_confidence_bar_empty(self) -> None:
        """0% confidence should show empty bar."""
        signal = create_test_signal(confidence=0.0)
        result = format_signal(signal)
        
        assert "0%" in result
        assert "░░░░░░░░░░" in result


class TestSignalFormatter:
    """Tests for SignalFormatter class."""
    
    def test_formatter_html_default(self) -> None:
        """Formatter should use HTML by default."""
        formatter = SignalFormatter()
        signal = create_test_signal()
        result = formatter.format(signal)
        
        assert "<b>" in result
    
    def test_formatter_plain_text_option(self) -> None:
        """Formatter should support plain text mode."""
        formatter = SignalFormatter(html=False)
        signal = create_test_signal()
        result = formatter.format(signal)
        
        assert "<b>" not in result
