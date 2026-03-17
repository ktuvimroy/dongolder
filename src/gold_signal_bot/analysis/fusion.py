"""Multi-indicator fusion engine for weighted signal scoring.

This module provides the FusionEngine class that combines technical indicators
using weighted scoring to produce more reliable trading signals.
"""

from dataclasses import dataclass, field

from .models import MLPrediction, PriceLevel, SentimentResult, SignalDirection, TechnicalSnapshot


@dataclass
class IndicatorWeight:
    """Configuration for indicator weights in fusion scoring.
    
    Weights should sum to 1.0 for normalized scoring.
    Default weights with advanced analysis enabled:
    - RSI (20%): Momentum indicator, good for reversals
    - MACD (25%): Trend + momentum
    - EMA (20%): Trend indicator, reliable direction
    - Bollinger (15%): Volatility/mean reversion
    - Sentiment (10%): News-based market sentiment
    - ML Pattern (10%): Historical pattern recognition
    
    Attributes:
        rsi: Weight for RSI indicator (default 0.20)
        macd: Weight for MACD indicator (default 0.25)
        ema: Weight for EMA indicator (default 0.20)
        bollinger: Weight for Bollinger Bands (default 0.15)
        sentiment: Weight for news sentiment (default 0.10)
        ml_pattern: Weight for ML pattern recognition (default 0.10)
    """
    rsi: float = 0.20
    macd: float = 0.25
    ema: float = 0.20
    bollinger: float = 0.15
    sentiment: float = 0.10
    ml_pattern: float = 0.10


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
        sentiment_contribution: How much sentiment affected the score
        ml_contribution: How much ML pattern recognition affected the score
    """
    bullish_score: float
    bearish_score: float
    direction: SignalDirection
    aligned_indicators: list[str] = field(default_factory=list)
    conflicting_indicators: list[str] = field(default_factory=list)
    sr_bonus: float = 0.0
    sentiment_contribution: float = 0.0
    ml_contribution: float = 0.0
    
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
        
        Note:
            Technical indicator weights are normalized to sum to 1.0 for
            backward compatibility. Use fuse_with_advanced() for sentiment
            and ML integration.
        """
        bullish_score = 0.0
        bearish_score = 0.0
        bullish_indicators: list[str] = []
        bearish_indicators: list[str] = []
        
        # Calculate total technical weight and normalization factor
        tech_weight_total = (
            self.weights.rsi + self.weights.macd + 
            self.weights.ema + self.weights.bollinger
        )
        # Normalize to 1.0 for backward compatibility
        norm_factor = 1.0 / tech_weight_total if tech_weight_total > 0 else 1.0
        
        # Process each indicator with normalized weights
        indicator_map = [
            ("RSI", snapshot.rsi, self.weights.rsi * norm_factor),
            ("MACD", snapshot.macd, self.weights.macd * norm_factor),
            ("EMA", snapshot.ema, self.weights.ema * norm_factor),
            ("Bollinger", snapshot.bollinger, self.weights.bollinger * norm_factor),
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

    def fuse_with_advanced(
        self,
        snapshot: TechnicalSnapshot,
        current_price: float,
        support: PriceLevel | None = None,
        resistance: PriceLevel | None = None,
        sentiment: SentimentResult | None = None,
        ml_prediction: MLPrediction | None = None,
    ) -> FusionResult:
        """Fuse indicators with optional sentiment and ML inputs.
        
        This extends the base fuse() method to incorporate:
        - News sentiment analysis (10% weight when available)
        - ML pattern recognition predictions (10% weight when available)
        
        If sentiment/ML not provided, their weight is redistributed 
        proportionally to technical indicators.
        
        Args:
            snapshot: Technical indicator snapshot to analyze
            current_price: Current market price for S/R proximity check
            support: Nearest support level (optional)
            resistance: Nearest resistance level (optional)
            sentiment: SentimentResult from news analysis (optional)
            ml_prediction: MLPrediction from pattern recognition (optional)
            
        Returns:
            FusionResult with weighted scores, direction, and advanced contributions
        """
        bullish_score = 0.0
        bearish_score = 0.0
        bullish_indicators: list[str] = []
        bearish_indicators: list[str] = []
        sentiment_contribution = 0.0
        ml_contribution = 0.0
        
        # Calculate total technical weight for potential redistribution
        tech_weight_total = (
            self.weights.rsi + self.weights.macd + 
            self.weights.ema + self.weights.bollinger
        )
        
        # Determine available advanced weights for redistribution
        advanced_weight_to_redistribute = 0.0
        if sentiment is None or sentiment.article_count == 0:
            advanced_weight_to_redistribute += self.weights.sentiment
        if ml_prediction is None or ml_prediction.probability <= 0.5:
            advanced_weight_to_redistribute += self.weights.ml_pattern
        
        # Scale factor for technical weights (redistribute unavailable advanced weights)
        if advanced_weight_to_redistribute > 0:
            scale_factor = (tech_weight_total + advanced_weight_to_redistribute) / tech_weight_total
        else:
            scale_factor = 1.0
        
        # Process technical indicators with scaled weights
        indicator_map = [
            ("RSI", snapshot.rsi, self.weights.rsi * scale_factor),
            ("MACD", snapshot.macd, self.weights.macd * scale_factor),
            ("EMA", snapshot.ema, self.weights.ema * scale_factor),
            ("Bollinger", snapshot.bollinger, self.weights.bollinger * scale_factor),
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
        
        # Process sentiment if available
        if sentiment is not None and sentiment.article_count > 0:
            # Use absolute score scaled by weight
            contribution = abs(sentiment.score) * self.weights.sentiment
            sentiment_contribution = contribution
            
            if sentiment.signal == SignalDirection.BULLISH:
                bullish_score += contribution
                bullish_indicators.append("Sentiment")
            elif sentiment.signal == SignalDirection.BEARISH:
                bearish_score += contribution
                bearish_indicators.append("Sentiment")
        
        # Process ML prediction if available and confident
        if ml_prediction is not None and ml_prediction.probability > 0.5:
            # Use probability scaled by weight
            contribution = ml_prediction.probability * self.weights.ml_pattern
            ml_contribution = contribution
            
            if ml_prediction.direction == SignalDirection.BULLISH:
                bullish_score += contribution
                bullish_indicators.append("ML Pattern")
            elif ml_prediction.direction == SignalDirection.BEARISH:
                bearish_score += contribution
                bearish_indicators.append("ML Pattern")
        
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
            proximity = abs(current_price - support.price) / current_price
            if proximity <= self.SR_PROXIMITY_PERCENT:
                sr_bonus = self.SR_BONUS
                bullish_score += sr_bonus
        
        elif preliminary_direction == SignalDirection.BEARISH and resistance:
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
            sentiment_contribution=sentiment_contribution,
            ml_contribution=ml_contribution,
        )
