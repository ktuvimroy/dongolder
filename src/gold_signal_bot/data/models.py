"""Data models for gold price storage and analysis.

This module provides dataclasses for spot prices and OHLC candles,
plus a Timeframe enum for multi-timeframe analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Timeframe(str, Enum):
    """Supported candle timeframes for analysis.
    
    Values match common charting conventions:
    - H1: 1-hour candles
    - H4: 4-hour candles  
    - DAILY: Daily candles
    """
    H1 = "1H"
    H4 = "4H"
    DAILY = "D"


@dataclass
class SpotPrice:
    """Raw spot price from API.
    
    Represents a single price observation at a point in time.
    Used as input for candle aggregation.
    
    Attributes:
        timestamp: UTC datetime of the price observation.
        price: XAU/USD price per troy ounce.
    """
    timestamp: datetime
    price: float


@dataclass
class OHLC:
    """Aggregated OHLC candle data.
    
    Represents price action over a specific time period.
    Used for technical analysis and signal generation.
    
    Attributes:
        timestamp: Candle open time (UTC).
        open: First price in the period.
        high: Highest price in the period.
        low: Lowest price in the period.
        close: Last price in the period.
        timeframe: Candle duration (1H, 4H, or Daily).
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    timeframe: Timeframe
