"""Data models for technical analysis results.

This module provides dataclasses for individual indicator outputs
and combined technical snapshots.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalDirection(str, Enum):
    """Direction of a trading signal."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class RSIResult:
    """RSI indicator result.
    
    Attributes:
        value: RSI value (0-100)
        signal: Oversold (<30) = bullish, Overbought (>70) = bearish
    """
    value: float
    signal: SignalDirection
    
    @classmethod
    def from_value(cls, value: float) -> "RSIResult":
        """Create RSIResult with auto-detected signal."""
        if value < 30:
            signal = SignalDirection.BULLISH  # Oversold
        elif value > 70:
            signal = SignalDirection.BEARISH  # Overbought
        else:
            signal = SignalDirection.NEUTRAL
        return cls(value=value, signal=signal)


@dataclass
class MACDResult:
    """MACD indicator result.
    
    Attributes:
        macd_line: MACD line value (fast EMA - slow EMA)
        signal_line: Signal line value (EMA of MACD)
        histogram: MACD histogram (MACD - signal)
        signal: Bullish if MACD > signal, bearish if MACD < signal
    """
    macd_line: float
    signal_line: float
    histogram: float
    signal: SignalDirection
    
    @classmethod
    def from_values(cls, macd: float, signal: float, hist: float) -> "MACDResult":
        """Create MACDResult with auto-detected signal."""
        if hist > 0:
            direction = SignalDirection.BULLISH
        elif hist < 0:
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL
        return cls(macd_line=macd, signal_line=signal, histogram=hist, signal=direction)


@dataclass
class EMAResult:
    """EMA indicator result.
    
    Attributes:
        ema_21: 21-period EMA value
        ema_50: 50-period EMA value
        price: Current close price
        signal: Bullish if price > both EMAs, bearish if price < both
    """
    ema_21: float
    ema_50: float
    price: float
    signal: SignalDirection
    
    @classmethod
    def from_values(cls, ema21: float, ema50: float, price: float) -> "EMAResult":
        """Create EMAResult with auto-detected signal."""
        if price > ema21 and price > ema50:
            signal = SignalDirection.BULLISH
        elif price < ema21 and price < ema50:
            signal = SignalDirection.BEARISH
        else:
            signal = SignalDirection.NEUTRAL
        return cls(ema_21=ema21, ema_50=ema50, price=price, signal=signal)


@dataclass
class BollingerResult:
    """Bollinger Bands indicator result.
    
    Attributes:
        upper: Upper band value
        middle: Middle band (SMA) value
        lower: Lower band value
        price: Current close price
        signal: Bullish near lower, bearish near upper
    """
    upper: float
    middle: float
    lower: float
    price: float
    signal: SignalDirection
    
    @classmethod
    def from_values(
        cls, upper: float, middle: float, lower: float, price: float
    ) -> "BollingerResult":
        """Create BollingerResult with auto-detected signal."""
        band_width = upper - lower
        if band_width > 0:
            position = (price - lower) / band_width
            if position < 0.2:  # Near lower band
                signal = SignalDirection.BULLISH
            elif position > 0.8:  # Near upper band
                signal = SignalDirection.BEARISH
            else:
                signal = SignalDirection.NEUTRAL
        else:
            signal = SignalDirection.NEUTRAL
        return cls(upper=upper, middle=middle, lower=lower, price=price, signal=signal)


@dataclass
class TechnicalSnapshot:
    """Combined technical indicator snapshot for a point in time.
    
    Attributes:
        timestamp: Time of the analysis
        rsi: RSI(14) result
        macd: MACD(12,26,9) result
        ema: EMA(21,50) result
        bollinger: Bollinger Bands(20,2) result
    """
    timestamp: datetime
    rsi: RSIResult | None
    macd: MACDResult | None
    ema: EMAResult | None
    bollinger: BollingerResult | None
    
    def bullish_count(self) -> int:
        """Count indicators showing bullish signal."""
        count = 0
        for result in [self.rsi, self.macd, self.ema, self.bollinger]:
            if result and result.signal == SignalDirection.BULLISH:
                count += 1
        return count
    
    def bearish_count(self) -> int:
        """Count indicators showing bearish signal."""
        count = 0
        for result in [self.rsi, self.macd, self.ema, self.bollinger]:
            if result and result.signal == SignalDirection.BEARISH:
                count += 1
        return count


@dataclass
class PriceLevel:
    """A significant price level (support or resistance).
    
    Attributes:
        price: The price level value.
        level_type: Whether this is support or resistance.
        strength: How many times price has touched this level (1-5 scale).
        last_touched: When price last interacted with this level.
    """
    price: float
    level_type: str  # "support" or "resistance"
    strength: int  # 1-5, based on touch count
    last_touched: datetime | None = None


@dataclass
class RawSignal:
    """Raw trading signal before fusion/filtering.
    
    Attributes:
        timestamp: When the signal was generated.
        direction: BUY or SELL.
        timeframe: The timeframe this signal applies to.
        entry_price: Suggested entry price.
        stop_loss: Suggested stop loss level.
        take_profit_1: First take profit target.
        take_profit_2: Second take profit target (optional).
        reasoning: List of reasons why this signal was generated.
        indicators: The technical snapshot that produced this signal.
        nearby_support: Closest support level (if any).
        nearby_resistance: Closest resistance level (if any).
    """
    timestamp: datetime
    direction: str  # "BUY" or "SELL"
    timeframe: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    reasoning: list[str]
    indicators: TechnicalSnapshot
    nearby_support: PriceLevel | None = None
    nearby_resistance: PriceLevel | None = None
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio for TP1."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit_1 - self.entry_price)
        if risk == 0:
            return 0.0
        return reward / risk
