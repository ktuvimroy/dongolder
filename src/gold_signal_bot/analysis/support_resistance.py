"""Support and resistance level detection.

This module provides algorithms to identify significant price levels
from OHLC candle data using swing high/low detection.
"""

from datetime import datetime, timezone

from ..data.models import OHLC, Timeframe
from ..data.repository import OHLCRepository
from .models import PriceLevel


class SupportResistanceDetector:
    """Detects support and resistance levels from price data.
    
    Uses swing high/low algorithm to identify significant price levels.
    Levels are clustered and ranked by how many times price has touched them.
    
    Example:
        detector = SupportResistanceDetector(ohlc_repo)
        levels = detector.detect_levels(Timeframe.H4, lookback=100)
        support = detector.nearest_support(current_price, levels)
    """
    
    # Cluster tolerance - levels within this % are merged
    CLUSTER_TOLERANCE = 0.003  # 0.3%
    
    def __init__(
        self,
        ohlc_repo: OHLCRepository,
        swing_period: int = 5
    ) -> None:
        """Initialize detector.
        
        Args:
            ohlc_repo: Repository to fetch candle data from.
            swing_period: Number of candles on each side to confirm swing.
        """
        self.ohlc_repo = ohlc_repo
        self.swing_period = swing_period
    
    def detect_swing_highs(self, candles: list[OHLC]) -> list[tuple[float, datetime]]:
        """Find swing high points in candle data.
        
        A swing high is a candle whose high is higher than the highs
        of the N candles before and after it.
        
        Args:
            candles: List of OHLC candles, sorted by timestamp ascending.
            
        Returns:
            List of (price, timestamp) tuples for each swing high.
        """
        swing_highs = []
        n = len(candles)
        period = self.swing_period
        
        for i in range(period, n - period):
            current_high = candles[i].high
            is_swing_high = True
            
            # Check candles before
            for j in range(i - period, i):
                if candles[j].high >= current_high:
                    is_swing_high = False
                    break
            
            # Check candles after
            if is_swing_high:
                for j in range(i + 1, i + period + 1):
                    if candles[j].high >= current_high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swing_highs.append((current_high, candles[i].timestamp))
        
        return swing_highs
    
    def detect_swing_lows(self, candles: list[OHLC]) -> list[tuple[float, datetime]]:
        """Find swing low points in candle data.
        
        A swing low is a candle whose low is lower than the lows
        of the N candles before and after it.
        
        Args:
            candles: List of OHLC candles, sorted by timestamp ascending.
            
        Returns:
            List of (price, timestamp) tuples for each swing low.
        """
        swing_lows = []
        n = len(candles)
        period = self.swing_period
        
        for i in range(period, n - period):
            current_low = candles[i].low
            is_swing_low = True
            
            # Check candles before
            for j in range(i - period, i):
                if candles[j].low <= current_low:
                    is_swing_low = False
                    break
            
            # Check candles after
            if is_swing_low:
                for j in range(i + 1, i + period + 1):
                    if candles[j].low <= current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swing_lows.append((current_low, candles[i].timestamp))
        
        return swing_lows
    
    def cluster_levels(
        self, 
        price_points: list[tuple[float, datetime]],
        level_type: str
    ) -> list[PriceLevel]:
        """Cluster nearby price points into single levels.
        
        Points within CLUSTER_TOLERANCE of each other are merged.
        Strength is based on how many points clustered together.
        
        Args:
            price_points: List of (price, timestamp) tuples.
            level_type: "support" or "resistance".
            
        Returns:
            List of PriceLevel objects, sorted by price.
        """
        if not price_points:
            return []
        
        # Sort by price
        sorted_points = sorted(price_points, key=lambda x: x[0])
        
        clusters: list[list[tuple[float, datetime]]] = []
        current_cluster: list[tuple[float, datetime]] = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            price, timestamp = sorted_points[i]
            cluster_avg = sum(p for p, _ in current_cluster) / len(current_cluster)
            
            # Check if within tolerance
            if abs(price - cluster_avg) / cluster_avg <= self.CLUSTER_TOLERANCE:
                current_cluster.append((price, timestamp))
            else:
                clusters.append(current_cluster)
                current_cluster = [(price, timestamp)]
        
        clusters.append(current_cluster)
        
        # Convert clusters to PriceLevels
        levels = []
        for cluster in clusters:
            avg_price = sum(p for p, _ in cluster) / len(cluster)
            strength = min(len(cluster), 5)  # Cap at 5
            last_touched = max(t for _, t in cluster)
            
            levels.append(PriceLevel(
                price=round(avg_price, 2),
                level_type=level_type,
                strength=strength,
                last_touched=last_touched,
            ))
        
        return levels
    
    def detect_levels(
        self,
        timeframe: Timeframe,
        lookback: int = 100
    ) -> list[PriceLevel]:
        """Detect all support and resistance levels.
        
        Args:
            timeframe: Timeframe to analyze.
            lookback: Number of candles to analyze.
            
        Returns:
            List of all detected price levels.
        """
        candles = self.ohlc_repo.get_latest(timeframe=timeframe, limit=lookback)
        
        if len(candles) < self.swing_period * 2 + 1:
            return []
        
        # Detect swing points
        swing_highs = self.detect_swing_highs(candles)
        swing_lows = self.detect_swing_lows(candles)
        
        # Cluster into levels
        resistance_levels = self.cluster_levels(swing_highs, "resistance")
        support_levels = self.cluster_levels(swing_lows, "support")
        
        # Combine and sort by price
        all_levels = resistance_levels + support_levels
        all_levels.sort(key=lambda x: x.price)
        
        return all_levels
    
    def nearest_support(
        self,
        current_price: float,
        levels: list[PriceLevel]
    ) -> PriceLevel | None:
        """Find nearest support level below current price.
        
        Args:
            current_price: Current market price.
            levels: List of detected price levels.
            
        Returns:
            Nearest support level, or None if none found.
        """
        support_below = [
            level for level in levels
            if level.level_type == "support" and level.price < current_price
        ]
        
        if not support_below:
            return None
        
        return max(support_below, key=lambda x: x.price)
    
    def nearest_resistance(
        self,
        current_price: float,
        levels: list[PriceLevel]
    ) -> PriceLevel | None:
        """Find nearest resistance level above current price.
        
        Args:
            current_price: Current market price.
            levels: List of detected price levels.
            
        Returns:
            Nearest resistance level, or None if none found.
        """
        resistance_above = [
            level for level in levels
            if level.level_type == "resistance" and level.price > current_price
        ]
        
        if not resistance_above:
            return None
        
        return min(resistance_above, key=lambda x: x.price)
