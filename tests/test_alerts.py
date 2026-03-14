"""Tests for AlertManager alert system."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gold_signal_bot.analysis.models import (
    PriceLevel,
    RawSignal,
    RSIResult,
    SignalDirection,
    TechnicalSnapshot,
)
from gold_signal_bot.data.models import Timeframe
from gold_signal_bot.telegram.alerts import AlertManager


def create_test_signal(
    direction: str = "BUY",
    timeframe: str = "1H",
    entry: float = 2000.00,
) -> RawSignal:
    """Create a test signal with default values."""
    snapshot = TechnicalSnapshot(
        timestamp=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
        rsi=RSIResult(value=28.0, signal=SignalDirection.BULLISH),
        macd=None,
        ema=None,
        bollinger=None,
    )
    
    return RawSignal(
        timestamp=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
        direction=direction,
        timeframe=timeframe,
        entry_price=entry,
        stop_loss=entry * 0.995,
        take_profit_1=entry * 1.01,
        take_profit_2=entry * 1.02,
        reasoning=["Test reason"],
        indicators=snapshot,
        nearby_support=None,
        nearby_resistance=None,
    )


class TestAlertManagerCheckAndAlert:
    """Tests for check_and_alert method."""
    
    @pytest.mark.asyncio
    async def test_sends_signal_when_generated(self) -> None:
        """When SignalGenerator returns a signal, it should be sent."""
        # Create mocks
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        mock_signal_gen = MagicMock()
        test_signal = create_test_signal(direction="BUY", timeframe="1H")
        mock_signal_gen.generate_signal.return_value = test_signal
        
        # Create AlertManager with H1 only
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # Execute
        sent_signals = await alert_mgr.check_and_alert()
        
        # Verify
        assert len(sent_signals) == 1
        assert sent_signals[0] == test_signal
        mock_bot.send_signal.assert_called_once_with(test_signal)
    
    @pytest.mark.asyncio
    async def test_no_send_when_no_signal(self) -> None:
        """When SignalGenerator returns None, nothing should be sent."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.return_value = None
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        sent_signals = await alert_mgr.check_and_alert()
        
        assert len(sent_signals) == 0
        mock_bot.send_signal.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_multiple_timeframes_sends_multiple_signals(self) -> None:
        """Multiple timeframes with signals should all be sent."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        signal_h1 = create_test_signal(direction="BUY", timeframe="1H")
        signal_h4 = create_test_signal(direction="SELL", timeframe="4H")
        
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.side_effect = [signal_h1, signal_h4]
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1, Timeframe.H4],
        )
        
        sent_signals = await alert_mgr.check_and_alert()
        
        assert len(sent_signals) == 2
        assert mock_bot.send_signal.call_count == 2


class TestDuplicatePrevention:
    """Tests for duplicate signal prevention."""
    
    @pytest.mark.asyncio
    async def test_duplicate_signal_not_sent_within_window(self) -> None:
        """Same signal within 1 hour should not be re-sent."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        test_signal = create_test_signal(direction="BUY", timeframe="1H")
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.return_value = test_signal
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # First call - should send
        sent_1 = await alert_mgr.check_and_alert()
        assert len(sent_1) == 1
        
        # Second call - should NOT send (duplicate)
        sent_2 = await alert_mgr.check_and_alert()
        assert len(sent_2) == 0
        
        # Verify only one send overall
        assert mock_bot.send_signal.call_count == 1
    
    @pytest.mark.asyncio
    async def test_different_direction_not_duplicate(self) -> None:
        """Same timeframe but different direction should still send."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        signal_buy = create_test_signal(direction="BUY", timeframe="1H")
        signal_sell = create_test_signal(direction="SELL", timeframe="1H")
        
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.side_effect = [signal_buy, signal_sell]
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # First call - BUY signal
        sent_1 = await alert_mgr.check_and_alert()
        assert len(sent_1) == 1
        
        # Second call - SELL signal (different direction)
        sent_2 = await alert_mgr.check_and_alert()
        assert len(sent_2) == 1
        
        # Both should have been sent
        assert mock_bot.send_signal.call_count == 2
    
    @pytest.mark.asyncio
    async def test_signal_after_window_expires_sends(self) -> None:
        """Signal after duplicate window expires should be sent."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        test_signal = create_test_signal(direction="BUY", timeframe="1H")
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.return_value = test_signal
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # First call - should send
        sent_1 = await alert_mgr.check_and_alert()
        assert len(sent_1) == 1
        
        # Manually expire the duplicate window by setting old timestamp
        key = ("1H", "BUY")
        alert_mgr._last_signals[key] = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Third call after window expired - should send
        sent_3 = await alert_mgr.check_and_alert()
        assert len(sent_3) == 1
        
        assert mock_bot.send_signal.call_count == 2
    
    def test_clear_signal_history(self) -> None:
        """clear_signal_history should reset duplicate tracking."""
        mock_bot = MagicMock()
        mock_signal_gen = MagicMock()
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
        )
        
        # Add some history
        alert_mgr._last_signals[("1H", "BUY")] = datetime.now(timezone.utc)
        assert len(alert_mgr._last_signals) == 1
        
        # Clear it
        alert_mgr.clear_signal_history()
        assert len(alert_mgr._last_signals) == 0


class TestAlertManagerLifecycle:
    """Tests for AlertManager start/stop."""
    
    def test_default_timeframes(self) -> None:
        """Default timeframes should be H1 and H4."""
        mock_bot = MagicMock()
        mock_signal_gen = MagicMock()
        
        alert_mgr = AlertManager(mock_bot, mock_signal_gen)
        
        assert Timeframe.H1 in alert_mgr.timeframes
        assert Timeframe.H4 in alert_mgr.timeframes
        assert len(alert_mgr.timeframes) == 2
    
    def test_custom_timeframes(self) -> None:
        """Custom timeframes should override defaults."""
        mock_bot = MagicMock()
        mock_signal_gen = MagicMock()
        
        alert_mgr = AlertManager(
            mock_bot,
            mock_signal_gen,
            timeframes=[Timeframe.DAILY],
        )
        
        assert alert_mgr.timeframes == [Timeframe.DAILY]
    
    @pytest.mark.asyncio
    async def test_run_continuous_with_max_iterations(self) -> None:
        """run_continuous should stop after max_iterations."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.return_value = None
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # Run 3 iterations with 0.01s interval
        await alert_mgr.run_continuous(interval_seconds=0.01, max_iterations=3)
        
        # Should have called generate_signal 3 times
        assert mock_signal_gen.generate_signal.call_count == 3
        
        # Should not be running after completion
        assert not alert_mgr.is_running
    
    def test_stop_sets_running_false(self) -> None:
        """stop() should set _running to False."""
        mock_bot = MagicMock()
        mock_signal_gen = MagicMock()
        
        alert_mgr = AlertManager(mock_bot, mock_signal_gen)
        alert_mgr._running = True
        
        alert_mgr.stop()
        
        assert not alert_mgr._running


class TestAlertManagerErrorHandling:
    """Tests for error handling in AlertManager."""
    
    @pytest.mark.asyncio
    async def test_generator_exception_doesnt_crash(self) -> None:
        """Exception in signal generator should not crash check_and_alert."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=True)
        
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.side_effect = Exception("Test error")
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        # Should not raise, should return empty list
        sent_signals = await alert_mgr.check_and_alert()
        assert len(sent_signals) == 0
    
    @pytest.mark.asyncio
    async def test_bot_failure_handled_gracefully(self) -> None:
        """Failed send should not crash and not count as sent."""
        mock_bot = MagicMock()
        mock_bot.send_signal = AsyncMock(return_value=False)  # Simulate failure
        
        test_signal = create_test_signal()
        mock_signal_gen = MagicMock()
        mock_signal_gen.generate_signal.return_value = test_signal
        
        alert_mgr = AlertManager(
            telegram_bot=mock_bot,
            signal_generator=mock_signal_gen,
            timeframes=[Timeframe.H1],
        )
        
        sent_signals = await alert_mgr.check_and_alert()
        
        # Should not include failed signal
        assert len(sent_signals) == 0
        # Should have tried to send
        mock_bot.send_signal.assert_called_once()
