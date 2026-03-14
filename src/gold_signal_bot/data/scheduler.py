"""Async scheduler for periodic data fetching.

This module provides the DataScheduler class that runs periodic fetches
of gold prices, stores them to the database, and updates candles.
"""

import asyncio
import logging
from datetime import datetime, timezone

from .aggregator import CandleAggregator
from .fetcher import DataFetcher
from .models import SpotPrice
from .repository import SpotPriceRepository


class DataScheduler:
    """Schedules periodic data fetches with error handling.
    
    Runs the data collection pipeline on a configurable interval:
    1. Fetches current XAU/USD price from Alpha Vantage
    2. Stores the spot price to SQLite
    3. Updates all timeframe candles (1H, 4H, Daily)
    
    Features:
    - Graceful start/stop lifecycle
    - Error handling that doesn't crash the loop
    - Single fetch method for testing/manual use
    
    Example:
        async with DataFetcher() as fetcher:
            scheduler = DataScheduler(fetcher, spot_repo, aggregator)
            await scheduler.start()
            # Runs until stopped
            await scheduler.stop()
    """
    
    def __init__(
        self,
        fetcher: DataFetcher,
        spot_repo: SpotPriceRepository,
        aggregator: CandleAggregator,
        interval_seconds: int = 900,
    ) -> None:
        """Initialize scheduler.
        
        Args:
            fetcher: DataFetcher instance for API calls.
            spot_repo: Repository for storing spot prices.
            aggregator: CandleAggregator for updating candles.
            interval_seconds: Fetch interval in seconds (default 900 = 15 min).
        """
        self.fetcher = fetcher
        self.spot_repo = spot_repo
        self.aggregator = aggregator
        self.interval = interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self.logger = logging.getLogger(__name__)
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._running
    
    async def start(self) -> None:
        """Start the scheduler loop.
        
        Creates an async task that runs until stop() is called.
        Multiple calls to start() are ignored if already running.
        """
        if self._running:
            self.logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self.logger.info(
            f"DataScheduler started with {self.interval}s interval"
        )
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully.
        
        Cancels the running task and waits for cleanup.
        Safe to call even if not running.
        """
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        self.logger.info("DataScheduler stopped")
    
    async def _run_loop(self) -> None:
        """Main scheduler loop.
        
        Runs fetch_and_store on interval until stopped.
        Catches and logs errors without crashing the loop.
        """
        while self._running:
            try:
                await self._fetch_and_store()
            except asyncio.CancelledError:
                # Propagate cancellation
                raise
            except Exception as e:
                # Log but don't crash - continue to next interval
                self.logger.error(f"Fetch failed: {e}", exc_info=True)
            
            if self._running:
                await asyncio.sleep(self.interval)
    
    async def _fetch_and_store(self) -> SpotPrice:
        """Fetch current price, store it, and update candles.
        
        Returns:
            The stored SpotPrice.
            
        Raises:
            AlphaVantageError: If fetch fails.
        """
        # 1. Fetch current spot price
        price_data = await self.fetcher.fetch_gold_spot()
        
        # 2. Create SpotPrice from API response
        spot = SpotPrice(
            timestamp=datetime.now(timezone.utc),
            price=price_data["price"]
        )
        
        # 3. Save to repository
        self.spot_repo.save(spot)
        self.logger.info(f"Stored spot price: ${spot.price:.2f}")
        
        # 4. Update candles for all timeframes
        updated = self.aggregator.update_current_candles()
        for tf, candle in updated.items():
            if candle:
                self.logger.debug(
                    f"Updated {tf.value} candle: "
                    f"O={candle.open:.2f} H={candle.high:.2f} "
                    f"L={candle.low:.2f} C={candle.close:.2f}"
                )
        
        return spot
    
    async def fetch_once(self) -> SpotPrice:
        """Perform a single fetch (for testing/manual use).
        
        Same as _fetch_and_store but public. Useful for:
        - Testing the pipeline
        - Manual data collection
        - Integration tests
        
        Returns:
            The stored SpotPrice.
            
        Raises:
            AlphaVantageError: If fetch fails.
        """
        return await self._fetch_and_store()
