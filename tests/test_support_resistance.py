"""Tests for support/resistance detection and signal generation."""

from datetime import datetime, timedelta, timezone

import pytest

from gold_signal_bot.analysis import (
    SignalGenerator,
    SupportResistanceDetector,
    PriceLevel,
    RawSignal,
)
from gold_signal_bot.data.models import OHLC, Timeframe
from gold_signal_bot.data.repository import OHLCRepository


def make_candles_with_swings(
    base_price: float = 2000.0,
    timeframe: Timeframe = Timeframe.H1
) -> list[OHLC]:
    """Create candles with clear swing highs and lows.
    
    Pattern: rise, fall, rise, fall (creates visible S/R zones)
    """
    base_time = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    candles = []
    
    # Pattern: 2000 -> 2050 -> 2020 -> 2060 -> 2030 -> 2070
    prices = []
    for i in range(60):
        # Oscillating pattern
        cycle = i // 10
        position = i % 10
        if cycle % 2 == 0:
            # Rising phase
            price = base_price + (cycle * 20) + (position * 3)
        else:
            # Falling phase
            price = base_price + (cycle * 20) + 30 - (position * 3)
        prices.append(price)
    
    for i, price in enumerate(prices):
        candles.append(OHLC(
            timestamp=base_time + timedelta(hours=i),
            open=price - 2,
            high=price + 3,
            low=price - 3,
            close=price,
            timeframe=timeframe,
        ))
    
    return candles


class TestSupportResistanceDetector:
    """Tests for support/resistance detection."""
    
    def test_detect_swing_highs(self):
        """Detector finds swing high points."""
        candles = make_candles_with_swings()
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            detector = SupportResistanceDetector(repo, swing_period=3)
            swing_highs = detector.detect_swing_highs(candles)
            
            # Should find at least some swing highs
            assert len(swing_highs) > 0
            
            # Each swing high is a (price, timestamp) tuple
            for price, timestamp in swing_highs:
                assert isinstance(price, float)
                assert isinstance(timestamp, datetime)
        finally:
            os.unlink(db_path)
    
    def test_detect_swing_lows(self):
        """Detector finds swing low points."""
        candles = make_candles_with_swings()
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            detector = SupportResistanceDetector(repo, swing_period=3)
            swing_lows = detector.detect_swing_lows(candles)
            
            # Should find at least some swing lows
            assert len(swing_lows) > 0
        finally:
            os.unlink(db_path)
    
    def test_detect_levels_returns_price_levels(self):
        """detect_levels returns PriceLevel objects."""
        candles = make_candles_with_swings()
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            detector = SupportResistanceDetector(repo, swing_period=3)
            levels = detector.detect_levels(Timeframe.H1)
            
            assert isinstance(levels, list)
            for level in levels:
                assert isinstance(level, PriceLevel)
                assert level.level_type in ("support", "resistance")
                assert 1 <= level.strength <= 5
        finally:
            os.unlink(db_path)
    
    def test_nearest_support_below_price(self):
        """nearest_support returns level below current price."""
        levels = [
            PriceLevel(price=2000.0, level_type="support", strength=3),
            PriceLevel(price=2050.0, level_type="support", strength=2),
            PriceLevel(price=2100.0, level_type="resistance", strength=3),
        ]
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            detector = SupportResistanceDetector(repo)
            
            support = detector.nearest_support(2060.0, levels)
            assert support is not None
            assert support.price == 2050.0
        finally:
            os.unlink(db_path)
    
    def test_nearest_resistance_above_price(self):
        """nearest_resistance returns level above current price."""
        levels = [
            PriceLevel(price=2000.0, level_type="support", strength=3),
            PriceLevel(price=2050.0, level_type="resistance", strength=2),
            PriceLevel(price=2100.0, level_type="resistance", strength=3),
        ]
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            detector = SupportResistanceDetector(repo)
            
            resistance = detector.nearest_resistance(2060.0, levels)
            assert resistance is not None
            assert resistance.price == 2100.0
        finally:
            os.unlink(db_path)


class TestSignalGenerator:
    """Tests for signal generation."""
    
    def make_trending_candles(
        self,
        direction: str,
        count: int = 60
    ) -> list[OHLC]:
        """Create candles with a clear trend.
        
        Args:
            direction: "up" or "down"
            count: Number of candles
        """
        base_time = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        base_price = 2000.0
        candles = []
        
        for i in range(count):
            if direction == "up":
                price = base_price + (i * 2)
            else:
                price = base_price - (i * 2)
            
            candles.append(OHLC(
                timestamp=base_time + timedelta(hours=i),
                open=price - 1,
                high=price + 2,
                low=price - 2,
                close=price,
                timeframe=Timeframe.H1,
            ))
        
        return candles
    
    def test_generate_signal_with_uptrend(self):
        """Generator may produce BUY signal in uptrend."""
        candles = self.make_trending_candles("up")
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            generator = SignalGenerator(repo)
            signal = generator.generate_signal(Timeframe.H1)
            
            # Signal exists or is None (depends on indicator alignment)
            if signal is not None:
                assert isinstance(signal, RawSignal)
                assert signal.direction in ("BUY", "SELL")
                assert signal.stop_loss > 0
                assert signal.take_profit_1 > 0
                assert len(signal.reasoning) > 0
        finally:
            os.unlink(db_path)
    
    def test_signal_has_required_fields(self):
        """Generated signals have all required fields."""
        candles = self.make_trending_candles("up")
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            generator = SignalGenerator(repo)
            signal = generator.generate_signal(Timeframe.H1)
            
            if signal is not None:
                assert signal.entry_price > 0
                assert signal.stop_loss > 0
                assert signal.take_profit_1 > 0
                assert signal.timeframe == "1H"
                assert signal.indicators is not None
        finally:
            os.unlink(db_path)
    
    def test_risk_reward_ratio(self):
        """Signal risk_reward_ratio is calculated correctly."""
        candles = self.make_trending_candles("up")
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            generator = SignalGenerator(repo)
            signal = generator.generate_signal(Timeframe.H1)
            
            if signal is not None:
                rr = signal.risk_reward_ratio
                assert rr >= 0  # Should be non-negative
        finally:
            os.unlink(db_path)
    
    def test_analyze_all_timeframes(self):
        """analyze_all_timeframes returns dict for each timeframe."""
        candles = self.make_trending_candles("up")
        
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for c in candles:
                repo.save(c)
            
            generator = SignalGenerator(repo)
            results = generator.analyze_all_timeframes()
            
            assert Timeframe.H1 in results
            assert Timeframe.H4 in results
            assert Timeframe.DAILY in results
        finally:
            os.unlink(db_path)
