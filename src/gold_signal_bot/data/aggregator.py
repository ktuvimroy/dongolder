"""Candle aggregation for multi-timeframe analysis.

This module provides the CandleAggregator class that converts raw spot prices
into OHLC candles for 1H, 4H, and Daily timeframes.
"""

from datetime import datetime, timedelta, timezone

from .models import OHLC, SpotPrice, Timeframe
from .repository import OHLCRepository, SpotPriceRepository


class CandleAggregator:
    """Aggregates spot prices into OHLC candles for multiple timeframes.
    
    Converts raw spot price observations into aggregated candlestick data.
    Supports 1-hour, 4-hour, and daily timeframes. Candles are updated
    incrementally as new prices arrive - the close price reflects the
    latest price until the candle period ends.
    
    Example:
        aggregator = CandleAggregator(spot_repo, ohlc_repo)
        # Update all current candles
        candles = aggregator.update_current_candles()
        # Or aggregate a specific candle
        candle = aggregator.aggregate_candle(Timeframe.H1, candle_start)
    """
    
    def __init__(
        self, 
        spot_repo: SpotPriceRepository, 
        ohlc_repo: OHLCRepository
    ) -> None:
        """Initialize aggregator with repositories.
        
        Args:
            spot_repo: Repository for reading spot prices.
            ohlc_repo: Repository for writing OHLC candles.
        """
        self.spot_repo = spot_repo
        self.ohlc_repo = ohlc_repo
    
    def _get_candle_boundaries(
        self, 
        timeframe: Timeframe, 
        dt: datetime
    ) -> tuple[datetime, datetime]:
        """Get start and end time for a candle containing the given datetime.
        
        Args:
            timeframe: The candle timeframe.
            dt: A datetime that falls within the desired candle.
            
        Returns:
            Tuple of (candle_start, candle_end) datetimes in UTC.
        """
        # Ensure we're working in UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        
        if timeframe == Timeframe.H1:
            # Round down to the hour
            start = dt.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1) - timedelta(microseconds=1)
            
        elif timeframe == Timeframe.H4:
            # Round down to 0, 4, 8, 12, 16, 20 UTC
            hour_block = (dt.hour // 4) * 4
            start = dt.replace(hour=hour_block, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=4) - timedelta(microseconds=1)
            
        elif timeframe == Timeframe.DAILY:
            # Round down to 00:00 UTC
            start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        return start, end
    
    def aggregate_candle(
        self, 
        timeframe: Timeframe, 
        candle_start: datetime
    ) -> OHLC | None:
        """Aggregate spot prices into a single candle.
        
        Queries spot prices within the candle period and computes OHLC values.
        The candle is saved to the repository (upsert if exists).
        
        Args:
            timeframe: The candle timeframe.
            candle_start: The start time of the candle period.
            
        Returns:
            The aggregated OHLC candle, or None if no spot prices in range.
        """
        start, end = self._get_candle_boundaries(timeframe, candle_start)
        
        # Get spot prices in the candle range
        spots = self.spot_repo.get_range(start, end)
        
        if not spots:
            return None
        
        # Compute OHLC from spot prices
        prices = [s.price for s in spots]
        candle = OHLC(
            timestamp=start,
            open=spots[0].price,   # First price
            high=max(prices),      # Highest price
            low=min(prices),       # Lowest price
            close=spots[-1].price, # Last price
            timeframe=timeframe
        )
        
        # Save to repository (upsert)
        self.ohlc_repo.save(candle)
        
        return candle
    
    def update_current_candles(self) -> dict[Timeframe, OHLC | None]:
        """Update in-progress candles for all timeframes.
        
        Aggregates the current candle for each supported timeframe.
        This should be called after each new spot price is saved to
        keep candles up to date.
        
        Returns:
            Dict mapping timeframe to its current candle (or None if no data).
        """
        now = datetime.now(timezone.utc)
        result: dict[Timeframe, OHLC | None] = {}
        
        for timeframe in Timeframe:
            candle = self.aggregate_candle(timeframe, now)
            result[timeframe] = candle
        
        return result
    
    def backfill_candles(
        self, 
        timeframe: Timeframe, 
        start: datetime, 
        end: datetime
    ) -> list[OHLC]:
        """Generate candles for a historical period.
        
        Useful for backfilling candles from historical spot data.
        Iterates through candle periods from start to end.
        
        Args:
            timeframe: The candle timeframe.
            start: Start of the backfill period.
            end: End of the backfill period.
            
        Returns:
            List of generated OHLC candles.
        """
        candles: list[OHLC] = []
        
        # Get candle duration
        if timeframe == Timeframe.H1:
            delta = timedelta(hours=1)
        elif timeframe == Timeframe.H4:
            delta = timedelta(hours=4)
        else:  # DAILY
            delta = timedelta(days=1)
        
        # Align start to candle boundary
        candle_start, _ = self._get_candle_boundaries(timeframe, start)
        
        while candle_start <= end:
            candle = self.aggregate_candle(timeframe, candle_start)
            if candle:
                candles.append(candle)
            candle_start += delta
        
        return candles
