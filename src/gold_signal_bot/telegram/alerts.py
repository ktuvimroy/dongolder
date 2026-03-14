"""Alert manager for integrating signal generation with Telegram delivery.

This module provides AlertManager that connects the technical analysis
pipeline to Telegram notifications for real-time trading alerts.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from ..analysis.models import RawSignal
from ..analysis.signals import SignalGenerator
from ..data.models import Timeframe
from .bot import TelegramBot


class AlertManager:
    """Orchestrates signal generation and Telegram delivery.
    
    AlertManager is the "glue" between the analysis engine and Telegram.
    It periodically checks for signals across configured timeframes and
    sends alerts when trading opportunities are detected.
    
    Features:
    - Multi-timeframe monitoring (default: H1, H4)
    - Duplicate signal prevention (no re-alerts within 1 hour)
    - Graceful error handling (doesn't crash on errors)
    - Configurable check interval
    
    Example:
        bot = TelegramBot(settings)
        signal_gen = SignalGenerator(ohlc_repo)
        
        alert_mgr = AlertManager(bot, signal_gen)
        await alert_mgr.run_continuous()
    """
    
    # Time window to consider signals as duplicates
    DUPLICATE_WINDOW = timedelta(hours=1)
    
    def __init__(
        self,
        telegram_bot: TelegramBot,
        signal_generator: SignalGenerator,
        timeframes: list[Timeframe] | None = None,
    ) -> None:
        """Initialize the alert manager.
        
        Args:
            telegram_bot: TelegramBot instance for sending messages.
            signal_generator: SignalGenerator for creating signals.
            timeframes: Timeframes to monitor (default: [H1, H4]).
        """
        self.bot = telegram_bot
        self.signal_gen = signal_generator
        self.timeframes = timeframes or [Timeframe.H1, Timeframe.H4]
        
        # Track last signal per timeframe to prevent duplicates
        # Key: (timeframe, direction), Value: last signal timestamp
        self._last_signals: dict[tuple[str, str], datetime] = {}
        
        self.logger = logging.getLogger(__name__)
        self._running = False
    
    async def check_and_alert(self) -> list[RawSignal]:
        """Check for signals and send alerts.
        
        Iterates through configured timeframes, generates signals,
        and sends any new signals to Telegram.
        
        Returns:
            List of signals that were sent to Telegram.
        """
        sent_signals: list[RawSignal] = []
        
        for timeframe in self.timeframes:
            try:
                signal = self.signal_gen.generate_signal(timeframe)
                
                if signal is None:
                    self.logger.debug(f"No signal for {timeframe.value}")
                    continue
                
                # Check for duplicate
                if self._is_duplicate(signal):
                    self.logger.debug(
                        f"Skipping duplicate {signal.direction} signal for {timeframe.value}"
                    )
                    continue
                
                # Send to Telegram
                success = await self.bot.send_signal(signal)
                
                if success:
                    self._record_signal(signal)
                    sent_signals.append(signal)
                    self.logger.info(
                        f"Sent {signal.direction} signal for {timeframe.value} "
                        f"at ${signal.entry_price}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to send signal for {timeframe.value}"
                    )
                    
            except Exception as e:
                self.logger.error(
                    f"Error checking {timeframe.value}: {e}",
                    exc_info=True
                )
        
        return sent_signals
    
    async def run_continuous(
        self,
        interval_seconds: int = 900,
        max_iterations: int | None = None,
    ) -> None:
        """Run the alert manager continuously.
        
        Main entry point for running the bot. Checks for signals
        at specified intervals until stopped.
        
        Args:
            interval_seconds: Seconds between checks (default: 900 = 15 min).
            max_iterations: Maximum number of iterations (None = infinite).
                           Used mainly for testing.
        """
        self._running = True
        iteration = 0
        
        self.logger.info(
            f"AlertManager starting - interval: {interval_seconds}s, "
            f"timeframes: {[tf.value for tf in self.timeframes]}"
        )
        
        try:
            while self._running:
                if max_iterations is not None and iteration >= max_iterations:
                    break
                
                try:
                    signals = await self.check_and_alert()
                    if signals:
                        self.logger.info(f"Sent {len(signals)} signal(s)")
                    else:
                        self.logger.debug("No signals to send")
                except Exception as e:
                    self.logger.error(f"Error in check cycle: {e}", exc_info=True)
                
                iteration += 1
                await asyncio.sleep(interval_seconds)
                
        except asyncio.CancelledError:
            self.logger.info("AlertManager cancelled")
        finally:
            self._running = False
            self.logger.info("AlertManager stopped")
    
    def stop(self) -> None:
        """Signal the alert manager to stop."""
        self._running = False
    
    @property
    def is_running(self) -> bool:
        """Check if alert manager is running."""
        return self._running
    
    def _is_duplicate(self, signal: RawSignal) -> bool:
        """Check if signal is a duplicate of a recent signal.
        
        A signal is considered duplicate if we've sent a signal with
        the same timeframe and direction within DUPLICATE_WINDOW.
        
        Args:
            signal: The signal to check.
            
        Returns:
            True if this is a duplicate, False otherwise.
        """
        key = (signal.timeframe, signal.direction)
        last_time = self._last_signals.get(key)
        
        if last_time is None:
            return False
        
        now = datetime.now(timezone.utc)
        return (now - last_time) < self.DUPLICATE_WINDOW
    
    def _record_signal(self, signal: RawSignal) -> None:
        """Record that a signal was sent.
        
        Args:
            signal: The signal that was sent.
        """
        key = (signal.timeframe, signal.direction)
        self._last_signals[key] = datetime.now(timezone.utc)
    
    def clear_signal_history(self) -> None:
        """Clear the signal history (useful for testing)."""
        self._last_signals.clear()
