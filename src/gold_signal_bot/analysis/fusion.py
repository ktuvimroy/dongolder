"""Multi-indicator fusion engine for weighted signal scoring.

This module provides the FusionEngine class that combines technical indicators
using weighted scoring to produce more reliable trading signals.
"""

from dataclasses import dataclass, field

from .models import PriceLevel, SignalDirection, TechnicalSnapshot


@dataclass
class IndicatorWeight:
    """Configuration for indicator weights in fusion scoring.
    
    Weights should sum to 1.0 for normalized scoring.
    Default weights based on indicator reliability:
    - RSI (25%): Momentum indicator, good for reversals
    - MACD (30%): Trend + momentum, most weight for dual nature
    - EMA (25%): Trend indicator, reliable direction
    - Bollinger (20%): Volatility/mean reversion, supplementary
    
    Attributes:
        rsi: Weight for RSI indicator (default 0.25)
        macd: Weight for MACD indicator (default 0.30)
        ema: Weight for EMA indicator (default 0.25)
        bollinger: Weight for Bollinger Bands (default 0.20)
    """
    rsi: float = 0.25
    macd: float = 0.30
    ema: float = 0.25
    bollinger: float = 0.20


@dataclass
class FusionResult:
    """Result of multi-indicator fusion analysis.
    
    Attributes:
        bullish_score: Weighted bullish score (0.0 to 1.0)
        bearish_score: Weighted bearish score (0.0 to 1.0)
        direction: Final signal direction based on score comparison
        aligned_indicators: Names of indicators aligned with final direction
        conflicting_indicators: Names of indicators opposing final direction
        sr_bonus: Support/resistance proximity bonus applied
    """
    bullish_score: float
    bearish_score: float
    direction: SignalDirection
    aligned_indicators: list[str] = field(default_factory=list)
    conflicting_indicators: list[str] = field(default_factory=list)
    sr_bonus: float = 0.0
    
    @property
    def confidence(self) -> float:
        """Return the higher score as confidence level."""
        return max(self.bullish_score, self.bearish_score)
    
    @property
    def score_differential(self) -> float:
        """Difference between bullish and bearish scores."""
        return abs(self.bullish_score - self.bearish_score)


class FusionEngine:
    """Engine for combining multiple technical indicators into weighted scores.
    
    Uses configurable weights to produce a numerical fusion score that
    accounts for indicator alignment and support/resistance proximity.
    
    Example:
        >>> engine = FusionEngine()
        >>> result = engine.fuse(snapshot, current_price=2650.0, support=support_level)
        >>> print(f"Direction: {result.direction}, Score: {result.bullish_score}")
    """
    
    # S/R proximity threshold (1% of price)
    SR_PROXIMITY_PERCENT = 0.01
    # Bonus added when price is near relevant S/R level
    SR_BONUS = 0.10
    
    def __init__(self, weights: IndicatorWeight | None = None):
        """Initialize FusionEngine with indicator weights.
        
        Args:
            weights: Custom indicator weights. Uses defaults if not provided.
        """
        self.weights = weights or IndicatorWeight()
    
    def fuse(
        self,
        snapshot: TechnicalSnapshot,
        current_price: float,
        support: PriceLevel | None = None,
        resistance: PriceLevel | None = None,
    ) -> FusionResult:
        """Fuse multiple indicators into a weighted score.
        
        Args:
            snapshot: Technical indicator snapshot to analyze
            current_price: Current market price for S/R proximity check
            support: Nearest support level (optional)
            resistance: Nearest resistance level (optional)
            
        Returns:
            FusionResult with weighted scores and direction
        """
        bullish_score = 0.0
        bearish_score = 0.0
        bullish_indicators: list[str] = []
        bearish_indicators: list[str] = []
        
        # Process each indicator
        indicator_map = [
            ("RSI", snapshot.rsi, self.weights.rsi),
            ("MACD", snapshot.macd, self.weights.macd),
            ("EMA", snapshot.ema, self.weights.ema),
            ("Bollinger", snapshot.bollinger, self.weights.bollinger),
        ]
        
        for name, result, weight in indicator_map:
            if result is None:
                continue
                
            if result.signal == SignalDirection.BULLISH:
                bullish_score += weight
                bullish_indicators.append(name)
            elif result.signal == SignalDirection.BEARISH:
                bearish_score += weight
                bearish_indicators.append(name)
            # NEUTRAL signals contribute nothing
        
        # Determine preliminary direction
        if bullish_score > bearish_score:
            preliminary_direction = SignalDirection.BULLISH
        elif bearish_score > bullish_score:
            preliminary_direction = SignalDirection.BEARISH
        else:
            preliminary_direction = SignalDirection.NEUTRAL
        
        # Apply S/R proximity bonus
        sr_bonus = 0.0
        
        if preliminary_direction == SignalDirection.BULLISH and support:
            # Check if support is within 1% of current price
            proximity = abs(current_price - support.price) / current_price
            if proximity <= self.SR_PROXIMITY_PERCENT:
                sr_bonus = self.SR_BONUS
                bullish_score += sr_bonus
        
        elif preliminary_direction == SignalDirection.BEARISH and resistance:
            # Check if resistance is within 1% of current price
            proximity = abs(current_price - resistance.price) / current_price
            if proximity <= self.SR_PROXIMITY_PERCENT:
                sr_bonus = self.SR_BONUS
                bearish_score += sr_bonus
        
        # Cap scores at 1.0
        bullish_score = min(bullish_score, 1.0)
        bearish_score = min(bearish_score, 1.0)
        
        # Final direction determination
        if bullish_score > bearish_score:
            direction = SignalDirection.BULLISH
            aligned = bullish_indicators
            conflicting = bearish_indicators
        elif bearish_score > bullish_score:
            direction = SignalDirection.BEARISH
            aligned = bearish_indicators
            conflicting = bullish_indicators
        else:
            direction = SignalDirection.NEUTRAL
            aligned = []
            conflicting = []
        
        return FusionResult(
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            direction=direction,
            aligned_indicators=aligned,
            conflicting_indicators=conflicting,
            sr_bonus=sr_bonus,
        )
