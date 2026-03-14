"""Tests for multi-indicator fusion engine.

Tests verify weighted scoring, S/R proximity bonus, and edge cases.
"""

from datetime import datetime, timezone

import pytest

from gold_signal_bot.analysis.fusion import (
    FusionEngine,
    FusionResult,
    IndicatorWeight,
)
from gold_signal_bot.analysis.models import (
    BollingerResult,
    EMAResult,
    MACDResult,
    PriceLevel,
    RSIResult,
    SignalDirection,
    TechnicalSnapshot,
)


@pytest.fixture
def engine() -> FusionEngine:
    """Default fusion engine with standard weights."""
    return FusionEngine()


@pytest.fixture
def timestamp() -> datetime:
    """Fixed timestamp for tests."""
    return datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


def make_snapshot(
    timestamp: datetime,
    rsi_signal: SignalDirection | None = SignalDirection.NEUTRAL,
    macd_signal: SignalDirection | None = SignalDirection.NEUTRAL,
    ema_signal: SignalDirection | None = SignalDirection.NEUTRAL,
    bbands_signal: SignalDirection | None = SignalDirection.NEUTRAL,
) -> TechnicalSnapshot:
    """Create a TechnicalSnapshot with specified signal directions."""
    rsi = RSIResult(value=50.0, signal=rsi_signal) if rsi_signal else None
    macd = MACDResult(macd_line=0.0, signal_line=0.0, histogram=0.0, signal=macd_signal) if macd_signal else None
    ema = EMAResult(ema_21=2650.0, ema_50=2640.0, price=2655.0, signal=ema_signal) if ema_signal else None
    bollinger = BollingerResult(upper=2700.0, middle=2650.0, lower=2600.0, price=2655.0, signal=bbands_signal) if bbands_signal else None
    
    return TechnicalSnapshot(
        timestamp=timestamp,
        rsi=rsi,
        macd=macd,
        ema=ema,
        bollinger=bollinger,
    )


class TestAllBullish:
    """Test all indicators showing bullish signals."""
    
    def test_all_bullish_gives_max_score(self, engine: FusionEngine, timestamp: datetime):
        """With all bullish indicators, bullish score should be 1.0."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BULLISH,
            ema_signal=SignalDirection.BULLISH,
            bbands_signal=SignalDirection.BULLISH,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 1.0  # 0.25 + 0.30 + 0.25 + 0.20
        assert result.bearish_score == 0.0
        assert result.direction == SignalDirection.BULLISH
        assert len(result.aligned_indicators) == 4
        assert len(result.conflicting_indicators) == 0


class TestAllBearish:
    """Test all indicators showing bearish signals."""
    
    def test_all_bearish_gives_max_score(self, engine: FusionEngine, timestamp: datetime):
        """With all bearish indicators, bearish score should be 1.0."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BEARISH,
            macd_signal=SignalDirection.BEARISH,
            ema_signal=SignalDirection.BEARISH,
            bbands_signal=SignalDirection.BEARISH,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bearish_score == 1.0
        assert result.bullish_score == 0.0
        assert result.direction == SignalDirection.BEARISH
        assert len(result.aligned_indicators) == 4
        assert len(result.conflicting_indicators) == 0


class TestMixedSignals:
    """Test mixed bullish and bearish signals."""
    
    def test_mixed_signals_weighted_correctly(self, engine: FusionEngine, timestamp: datetime):
        """RSI=BULLISH, MACD=BEARISH, EMA=BULLISH, BBands=NEUTRAL."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,    # +0.25 bullish
            macd_signal=SignalDirection.BEARISH,   # +0.30 bearish
            ema_signal=SignalDirection.BULLISH,    # +0.25 bullish
            bbands_signal=SignalDirection.NEUTRAL, # no contribution
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 0.50  # RSI 0.25 + EMA 0.25
        assert result.bearish_score == 0.30  # MACD 0.30
        assert result.direction == SignalDirection.BULLISH  # 0.50 > 0.30
        assert "RSI" in result.aligned_indicators
        assert "EMA" in result.aligned_indicators
        assert "MACD" in result.conflicting_indicators
    
    def test_bearish_majority_wins(self, engine: FusionEngine, timestamp: datetime):
        """When bearish outweighs bullish, direction should be bearish."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,    # +0.25 bullish
            macd_signal=SignalDirection.BEARISH,   # +0.30 bearish
            ema_signal=SignalDirection.BEARISH,    # +0.25 bearish
            bbands_signal=SignalDirection.BEARISH, # +0.20 bearish
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 0.25
        assert result.bearish_score == 0.75  # MACD + EMA + BBands
        assert result.direction == SignalDirection.BEARISH


class TestSRProximityBonus:
    """Test support/resistance proximity bonus."""
    
    def test_bullish_with_nearby_support(self, engine: FusionEngine, timestamp: datetime):
        """Bullish signal with support within 1% gets +0.10 bonus."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BULLISH,
            ema_signal=SignalDirection.BULLISH,
            bbands_signal=SignalDirection.BULLISH,
        )
        
        # Support at 2640 is within 1% of 2650 (0.38%)
        support = PriceLevel(price=2640.0, level_type="support", strength=3)
        
        result = engine.fuse(snapshot, current_price=2650.0, support=support)
        
        # Score would be 1.10 but capped at 1.0
        assert result.bullish_score == 1.0
        assert result.sr_bonus == 0.10
    
    def test_bearish_with_nearby_resistance(self, engine: FusionEngine, timestamp: datetime):
        """Bearish signal with resistance within 1% gets +0.10 bonus."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BEARISH,
            macd_signal=SignalDirection.BEARISH,
            ema_signal=SignalDirection.BEARISH,
            bbands_signal=SignalDirection.BEARISH,
        )
        
        # Resistance at 2660 is within 1% of 2650 (0.38%)
        resistance = PriceLevel(price=2660.0, level_type="resistance", strength=3)
        
        result = engine.fuse(snapshot, current_price=2650.0, resistance=resistance)
        
        assert result.bearish_score == 1.0  # Capped
        assert result.sr_bonus == 0.10
    
    def test_no_bonus_when_sr_too_far(self, engine: FusionEngine, timestamp: datetime):
        """No bonus when S/R is more than 1% away."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BULLISH,
            ema_signal=SignalDirection.BULLISH,
            bbands_signal=SignalDirection.BULLISH,
        )
        
        # Support at 2600 is 1.9% away from 2650
        support = PriceLevel(price=2600.0, level_type="support", strength=3)
        
        result = engine.fuse(snapshot, current_price=2650.0, support=support)
        
        assert result.bullish_score == 1.0  # Full score without bonus
        assert result.sr_bonus == 0.0


class TestNeutralResult:
    """Test neutral/no signal scenarios."""
    
    def test_all_neutral_gives_neutral_direction(self, engine: FusionEngine, timestamp: datetime):
        """All neutral indicators should result in neutral direction."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.NEUTRAL,
            macd_signal=SignalDirection.NEUTRAL,
            ema_signal=SignalDirection.NEUTRAL,
            bbands_signal=SignalDirection.NEUTRAL,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 0.0
        assert result.bearish_score == 0.0
        assert result.direction == SignalDirection.NEUTRAL
        assert len(result.aligned_indicators) == 0
        assert len(result.conflicting_indicators) == 0


class TestPartialIndicators:
    """Test handling of missing/None indicators."""
    
    def test_only_rsi_and_macd(self, engine: FusionEngine, timestamp: datetime):
        """Only RSI and MACD present, EMA and BBands are None."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BEARISH,
            ema_signal=None,      # Not present
            bbands_signal=None,   # Not present
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        # Only RSI (0.25) and MACD (0.30) contribute
        assert result.bullish_score == 0.25  # RSI only
        assert result.bearish_score == 0.30  # MACD only
        assert result.direction == SignalDirection.BEARISH  # 0.30 > 0.25
        assert "RSI" in result.conflicting_indicators
        assert "MACD" in result.aligned_indicators
    
    def test_single_indicator(self, engine: FusionEngine, timestamp: datetime):
        """Only one indicator present."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=None,
            ema_signal=None,
            bbands_signal=None,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 0.25
        assert result.bearish_score == 0.0
        assert result.direction == SignalDirection.BULLISH


class TestCustomWeights:
    """Test custom indicator weights."""
    
    def test_custom_weights_applied(self, timestamp: datetime):
        """Engine uses custom weights when provided."""
        custom_weights = IndicatorWeight(
            rsi=0.40,      # More weight on RSI
            macd=0.20,     # Less on MACD
            ema=0.20,
            bollinger=0.20,
        )
        engine = FusionEngine(weights=custom_weights)
        
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BEARISH,
            ema_signal=SignalDirection.NEUTRAL,
            bbands_signal=SignalDirection.NEUTRAL,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.bullish_score == 0.40  # RSI with custom weight
        assert result.bearish_score == 0.20  # MACD with custom weight
        assert result.direction == SignalDirection.BULLISH


class TestFusionResultProperties:
    """Test FusionResult computed properties."""
    
    def test_confidence_is_max_score(self, engine: FusionEngine, timestamp: datetime):
        """Confidence should be the higher of the two scores."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,
            macd_signal=SignalDirection.BULLISH,
            ema_signal=SignalDirection.BEARISH,
            bbands_signal=SignalDirection.NEUTRAL,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        assert result.confidence == max(result.bullish_score, result.bearish_score)
    
    def test_score_differential(self, engine: FusionEngine, timestamp: datetime):
        """Score differential is absolute difference between scores."""
        snapshot = make_snapshot(
            timestamp,
            rsi_signal=SignalDirection.BULLISH,    # +0.25
            macd_signal=SignalDirection.BEARISH,   # +0.30
            ema_signal=SignalDirection.NEUTRAL,
            bbands_signal=SignalDirection.NEUTRAL,
        )
        
        result = engine.fuse(snapshot, current_price=2650.0)
        
        expected_diff = abs(0.25 - 0.30)
        assert result.score_differential == pytest.approx(expected_diff, abs=0.001)
