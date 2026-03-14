"""Raw signal generation from technical analysis.

This module provides SignalGenerator that combines technical indicators
with support/resistance levels to produce trading signals.
"""

from datetime import datetime, timezone

from ..data.models import OHLC, Timeframe
from ..data.repository import OHLCRepository
from .analyzer import TechnicalAnalyzer
from .fusion import FusionEngine
from .models import (
    PriceLevel,
    RawSignal,
    SignalDirection,
    TechnicalSnapshot,
)
from .support_resistance import SupportResistanceDetector


class SignalGenerator:
    """Generates raw trading signals from technical analysis.
    
    Combines technical indicators (RSI, MACD, EMA, BBands) with
    support/resistance levels to produce actionable signals.
    
    Signals are "raw" - not yet filtered by fusion engine or
    confidence thresholds. Each signal includes reasoning.
    
    Example:
        generator = SignalGenerator(ohlc_repo)
        signal = generator.generate_signal(Timeframe.H4)
        if signal:
            print(f"{signal.direction} at {signal.entry_price}")
            print(f"Reasons: {signal.reasoning}")
    """
    
    # ATR multipliers for SL/TP calculation (approximated as % of price)
    SL_MULTIPLIER = 0.005  # 0.5% from entry
    TP1_MULTIPLIER = 0.01  # 1% from entry
    TP2_MULTIPLIER = 0.02  # 2% from entry
    
    # Confidence thresholds for signal generation
    MIN_CONFIDENCE = 0.50  # 50% minimum to generate signal
    CONFLICT_PENALTY = 0.05  # 5% penalty per conflicting indicator
    
    def __init__(self, ohlc_repo: OHLCRepository) -> None:
        """Initialize signal generator.
        
        Args:
            ohlc_repo: Repository for price data.
        """
        self.ohlc_repo = ohlc_repo
        self.analyzer = TechnicalAnalyzer(ohlc_repo)
        self.sr_detector = SupportResistanceDetector(ohlc_repo)
        self.fusion_engine = FusionEngine()
    
    def generate_signal(
        self,
        timeframe: Timeframe
    ) -> RawSignal | None:
        """Generate a trading signal for the given timeframe.
        
        Uses FusionEngine for weighted indicator scoring and filters
        signals below MIN_CONFIDENCE threshold.
        
        Args:
            timeframe: Timeframe to analyze.
            
        Returns:
            RawSignal if conditions met, None otherwise.
        """
        # Get technical snapshot
        snapshot = self.analyzer.analyze(timeframe)
        
        # Get current price from latest candle
        candles = self.ohlc_repo.get_latest(timeframe=timeframe, limit=1)
        if not candles:
            return None
        
        current_price = candles[-1].close
        
        # Detect S/R levels
        levels = self.sr_detector.detect_levels(timeframe)
        support = self.sr_detector.nearest_support(current_price, levels)
        resistance = self.sr_detector.nearest_resistance(current_price, levels)
        
        # Use FusionEngine for weighted scoring
        fusion = self.fusion_engine.fuse(snapshot, current_price, support, resistance)
        
        # NEUTRAL direction = no signal
        if fusion.direction == SignalDirection.NEUTRAL:
            return None
        
        # Calculate confidence from fusion score
        if fusion.direction == SignalDirection.BULLISH:
            base_confidence = fusion.bullish_score
        else:
            base_confidence = fusion.bearish_score
        
        # Apply conflict penalty
        conflict_penalty = len(fusion.conflicting_indicators) * self.CONFLICT_PENALTY
        confidence = max(0.0, min(1.0, base_confidence - conflict_penalty))
        
        # Filter by minimum confidence
        if confidence < self.MIN_CONFIDENCE:
            return None
        
        # Generate signal based on direction
        if fusion.direction == SignalDirection.BULLISH:
            return self._create_buy_signal(
                snapshot, current_price, support, resistance, timeframe,
                confidence, fusion.aligned_indicators
            )
        else:
            return self._create_sell_signal(
                snapshot, current_price, support, resistance, timeframe,
                confidence, fusion.aligned_indicators
            )
        
        return None
    
    def _create_buy_signal(
        self,
        snapshot: TechnicalSnapshot,
        price: float,
        support: PriceLevel | None,
        resistance: PriceLevel | None,
        timeframe: Timeframe,
        confidence: float,
        aligned_indicators: list[str],
    ) -> RawSignal:
        """Create a BUY signal with entry/SL/TP."""
        reasoning = self._build_reasoning(
            snapshot, "BUY", support, resistance, price, confidence, aligned_indicators
        )
        
        # Calculate levels
        # SL below support if available, otherwise use multiplier
        if support and support.price < price:
            stop_loss = support.price - (price * 0.001)  # Slightly below support
        else:
            stop_loss = price * (1 - self.SL_MULTIPLIER)
        
        # TP at resistance if available, otherwise use multiplier
        if resistance and resistance.price > price:
            take_profit_1 = resistance.price
            take_profit_2 = resistance.price + (price * self.TP1_MULTIPLIER)
        else:
            take_profit_1 = price * (1 + self.TP1_MULTIPLIER)
            take_profit_2 = price * (1 + self.TP2_MULTIPLIER)
        
        return RawSignal(
            timestamp=snapshot.timestamp or datetime.now(timezone.utc),
            direction="BUY",
            timeframe=timeframe.value,
            entry_price=round(price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(take_profit_1, 2),
            take_profit_2=round(take_profit_2, 2),
            reasoning=reasoning,
            indicators=snapshot,
            nearby_support=support,
            nearby_resistance=resistance,
            confidence=confidence,
        )
    
    def _create_sell_signal(
        self,
        snapshot: TechnicalSnapshot,
        price: float,
        support: PriceLevel | None,
        resistance: PriceLevel | None,
        timeframe: Timeframe,
        confidence: float,
        aligned_indicators: list[str],
    ) -> RawSignal:
        """Create a SELL signal with entry/SL/TP."""
        reasoning = self._build_reasoning(
            snapshot, "SELL", support, resistance, price, confidence, aligned_indicators
        )
        
        # Calculate levels
        # SL above resistance if available, otherwise use multiplier
        if resistance and resistance.price > price:
            stop_loss = resistance.price + (price * 0.001)  # Slightly above resistance
        else:
            stop_loss = price * (1 + self.SL_MULTIPLIER)
        
        # TP at support if available, otherwise use multiplier
        if support and support.price < price:
            take_profit_1 = support.price
            take_profit_2 = support.price - (price * self.TP1_MULTIPLIER)
        else:
            take_profit_1 = price * (1 - self.TP1_MULTIPLIER)
            take_profit_2 = price * (1 - self.TP2_MULTIPLIER)
        
        return RawSignal(
            timestamp=snapshot.timestamp or datetime.now(timezone.utc),
            direction="SELL",
            timeframe=timeframe.value,
            entry_price=round(price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(take_profit_1, 2),
            take_profit_2=round(take_profit_2, 2),
            reasoning=reasoning,
            indicators=snapshot,
            nearby_support=support,
            nearby_resistance=resistance,
            confidence=confidence,
        )
    
    def _build_reasoning(
        self,
        snapshot: TechnicalSnapshot,
        direction: str,
        support: PriceLevel | None,
        resistance: PriceLevel | None,
        price: float,
        confidence: float,
        aligned_indicators: list[str],
    ) -> list[str]:
        """Build list of reasons for the signal."""
        reasons = []
        
        # Confidence context first
        tier = "HIGH" if confidence >= 0.80 else "MEDIUM" if confidence >= 0.60 else "LOW"
        reasons.append(f"Confidence: {confidence*100:.0f}% ({tier})")
        reasons.append(f"Indicators aligned: {', '.join(aligned_indicators)}")
        
        # RSI reason
        if snapshot.rsi:
            if direction == "BUY" and snapshot.rsi.signal == SignalDirection.BULLISH:
                reasons.append(f"RSI(14) oversold at {snapshot.rsi.value:.1f}")
            elif direction == "SELL" and snapshot.rsi.signal == SignalDirection.BEARISH:
                reasons.append(f"RSI(14) overbought at {snapshot.rsi.value:.1f}")
        
        # MACD reason
        if snapshot.macd:
            if direction == "BUY" and snapshot.macd.signal == SignalDirection.BULLISH:
                reasons.append("MACD bullish crossover")
            elif direction == "SELL" and snapshot.macd.signal == SignalDirection.BEARISH:
                reasons.append("MACD bearish crossover")
        
        # EMA reason
        if snapshot.ema:
            if direction == "BUY" and snapshot.ema.signal == SignalDirection.BULLISH:
                reasons.append(f"Price above EMA(21) at {snapshot.ema.ema_21:.2f}")
            elif direction == "SELL" and snapshot.ema.signal == SignalDirection.BEARISH:
                reasons.append(f"Price below EMA(21) at {snapshot.ema.ema_21:.2f}")
        
        # Bollinger reason
        if snapshot.bollinger:
            if direction == "BUY" and snapshot.bollinger.signal == SignalDirection.BULLISH:
                reasons.append("Price near lower Bollinger Band")
            elif direction == "SELL" and snapshot.bollinger.signal == SignalDirection.BEARISH:
                reasons.append("Price near upper Bollinger Band")
        
        # S/R reasons
        if direction == "BUY" and support:
            dist_pct = ((price - support.price) / price) * 100
            if dist_pct < 1.0:  # Within 1% of support
                reasons.append(f"Near support at {support.price:.2f} (strength: {support.strength})")
        
        if direction == "SELL" and resistance:
            dist_pct = ((resistance.price - price) / price) * 100
            if dist_pct < 1.0:  # Within 1% of resistance
                reasons.append(f"Near resistance at {resistance.price:.2f} (strength: {resistance.strength})")
        
        return reasons
    
    def analyze_all_timeframes(self) -> dict[Timeframe, RawSignal | None]:
        """Generate signals for all supported timeframes.
        
        Returns:
            Dict mapping timeframe to signal (or None if no signal).
        """
        results = {}
        for timeframe in Timeframe:
            results[timeframe] = self.generate_signal(timeframe)
        return results
