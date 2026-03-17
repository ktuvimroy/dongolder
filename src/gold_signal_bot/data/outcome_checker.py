"""Outcome checker for evaluating open signal results.

Periodically compares current spot price against each open signal's
take_profit_1 and stop_loss to mark signals as WIN, LOSS, or EXPIRED.
"""

import asyncio
import logging
from datetime import datetime, timezone

from .signal_history import SignalHistoryRepository, SignalRecord
from .repository import SpotPriceRepository


class OutcomeChecker:
    """Evaluates open trading signals against current price data.
    
    Runs as a periodic async task. Checks all OPEN signals and marks
    them WIN (hit TP1), LOSS (hit SL), or EXPIRED (too old).
    
    Uses the spot_prices table for current price — the same table
    that the data fetcher writes to continuously.
    """

    def __init__(
        self,
        signal_repo: SignalHistoryRepository,
        spot_repo: SpotPriceRepository,
        max_hours_open: int = 48,
    ) -> None:
        self.signal_repo = signal_repo
        self.spot_repo = spot_repo
        self.max_hours_open = max_hours_open
        self.logger = logging.getLogger(__name__)

    def _get_current_price(self) -> float | None:
        """Get latest gold spot price from repository. Returns None if no data."""
        prices = self.spot_repo.get_latest(limit=1)
        return prices[0].price if prices else None

    def _evaluate_signal(
        self, signal: SignalRecord, current_price: float
    ) -> tuple[str | None, float | None]:
        """
        Determine outcome for a single open signal.
        
        Returns:
            (outcome, pnl_pct) or (None, None) if still open.
            outcome: 'WIN', 'LOSS', or 'EXPIRED'
            pnl_pct: decimal (e.g. 0.011 = 1.1%). Positive = profit.
        """
        now = datetime.now(timezone.utc)
        # Handle both naive and aware datetimes from DB
        sent = signal.sent_at
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        hours_open = (now - sent).total_seconds() / 3600

        if signal.direction == "BUY":
            if current_price >= signal.take_profit_1:
                pnl = (signal.take_profit_1 - signal.entry_price) / signal.entry_price
                return "WIN", pnl
            elif current_price <= signal.stop_loss:
                pnl = (signal.stop_loss - signal.entry_price) / signal.entry_price
                return "LOSS", pnl
        else:  # SELL
            if current_price <= signal.take_profit_1:
                pnl = (signal.entry_price - signal.take_profit_1) / signal.entry_price
                return "WIN", pnl
            elif current_price >= signal.stop_loss:
                pnl = (signal.entry_price - signal.stop_loss) / signal.entry_price
                return "LOSS", pnl

        # Expire if open too long
        effective_max = signal.max_hours_open or self.max_hours_open
        if hours_open >= effective_max:
            pnl = (
                (current_price - signal.entry_price) / signal.entry_price
                if signal.direction == "BUY"
                else (signal.entry_price - current_price) / signal.entry_price
            )
            return "EXPIRED", pnl

        return None, None

    def check_open_signals(self) -> int:
        """
        Evaluate all OPEN signals. Updates outcomes in DB.
        
        Returns count of signals that were resolved (status changed from OPEN).
        """
        current_price = self._get_current_price()
        if current_price is None:
            self.logger.warning("No spot price data available; skipping outcome check")
            return 0

        open_signals = self.signal_repo.get_open_signals()
        if not open_signals:
            self.logger.debug("No open signals to evaluate")
            return 0

        resolved = 0
        for signal in open_signals:
            try:
                outcome, pnl = self._evaluate_signal(signal, current_price)
                if outcome:
                    self.signal_repo.update_outcome(
                        signal.signal_id, outcome, current_price, pnl
                    )
                    self.logger.info(
                        f"Signal {signal.signal_id[:8]}... resolved: "
                        f"{outcome} ({signal.direction} {signal.timeframe} "
                        f"entry={signal.entry_price:.2f} current={current_price:.2f} "
                        f"pnl={pnl*100:.2f}%)"
                    )
                    resolved += 1
            except Exception as e:
                self.logger.error(
                    f"Error evaluating signal {signal.signal_id}: {e}", exc_info=True
                )

        return resolved

    async def run_periodic(self, interval_seconds: int = 900) -> None:
        """Run outcome checks at regular intervals forever.
        
        Designed to run as an asyncio.create_task() alongside the main alert loop.
        """
        self.logger.info(
            f"OutcomeChecker starting — interval: {interval_seconds}s"
        )
        while True:
            try:
                resolved = self.check_open_signals()
                if resolved > 0:
                    self.logger.info(f"OutcomeChecker resolved {resolved} signal(s)")
            except Exception as e:
                self.logger.error(f"OutcomeChecker error: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)
