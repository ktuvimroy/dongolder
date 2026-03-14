"""Tests for technical indicator calculations."""

from datetime import datetime, timedelta, timezone

import pytest

from gold_signal_bot.analysis import (
    TechnicalAnalyzer,
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_bbands,
    SignalDirection,
)
from gold_signal_bot.data.models import OHLC, Timeframe
from gold_signal_bot.data.repository import OHLCRepository


def make_candles(prices: list[float], timeframe: Timeframe = Timeframe.H1) -> list[OHLC]:
    """Create OHLC candles from a list of close prices.
    
    For simplicity, OHLC are all set to the same price.
    """
    base_time = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    candles = []
    for i, price in enumerate(prices):
        candles.append(OHLC(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price * 1.001,  # Slight variation
            low=price * 0.999,
            close=price,
            timeframe=timeframe,
        ))
    return candles


class TestRSI:
    """Tests for RSI calculation."""
    
    def test_rsi_insufficient_data(self):
        """RSI returns None with fewer than 15 candles."""
        candles = make_candles([100.0] * 10)
        assert calculate_rsi(candles) is None
    
    def test_rsi_returns_value_in_range(self):
        """RSI returns value between 0 and 100."""
        # Create trending data
        prices = [2000.0 + i * 5 for i in range(30)]  # Uptrend
        candles = make_candles(prices)
        
        rsi = calculate_rsi(candles)
        assert rsi is not None
        assert 0 <= rsi <= 100
    
    def test_rsi_uptrend_high_value(self):
        """RSI in strong uptrend should be high (>50)."""
        prices = [2000.0 + i * 10 for i in range(30)]  # Strong uptrend
        candles = make_candles(prices)
        
        rsi = calculate_rsi(candles)
        assert rsi is not None
        assert rsi > 50


class TestMACD:
    """Tests for MACD calculation."""
    
    def test_macd_insufficient_data(self):
        """MACD returns None with fewer than 35 candles."""
        candles = make_candles([100.0] * 30)
        assert calculate_macd(candles) is None
    
    def test_macd_returns_three_values(self):
        """MACD returns tuple of (macd, signal, histogram)."""
        prices = [2000.0 + i * 2 for i in range(50)]
        candles = make_candles(prices)
        
        result = calculate_macd(candles)
        assert result is not None
        assert len(result) == 3
        macd, signal, hist = result
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(hist, float)


class TestEMA:
    """Tests for EMA calculation."""
    
    def test_ema_insufficient_data(self):
        """EMA returns None with insufficient candles."""
        candles = make_candles([100.0] * 10)
        assert calculate_ema(candles, period=21) is None
    
    def test_ema_tracks_price(self):
        """EMA should be close to recent prices."""
        prices = [2000.0] * 30
        candles = make_candles(prices)
        
        ema = calculate_ema(candles, period=21)
        assert ema is not None
        assert abs(ema - 2000.0) < 1.0  # Should be very close


class TestBollingerBands:
    """Tests for Bollinger Bands calculation."""
    
    def test_bbands_insufficient_data(self):
        """BBands returns None with fewer than 20 candles."""
        candles = make_candles([100.0] * 15)
        assert calculate_bbands(candles) is None
    
    def test_bbands_band_order(self):
        """Upper > Middle > Lower bands."""
        prices = [2000.0 + (i % 10) * 5 for i in range(30)]  # Some variation
        candles = make_candles(prices)
        
        result = calculate_bbands(candles)
        assert result is not None
        upper, middle, lower = result
        assert upper > middle > lower


class TestTechnicalAnalyzer:
    """Tests for TechnicalAnalyzer."""
    
    def test_analyzer_with_sufficient_data(self):
        """Analyzer returns snapshot with all indicators."""
        prices = [2000.0 + i * 2 for i in range(60)]
        candles = make_candles(prices)
        
        # Use file-based temp database to avoid in-memory connection issues
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for candle in candles:
                repo.save(candle)
            
            analyzer = TechnicalAnalyzer(repo)
            snapshot = analyzer.analyze(Timeframe.H1)
            
            assert snapshot.rsi is not None
            assert snapshot.macd is not None
            assert snapshot.ema is not None
            assert snapshot.bollinger is not None
        finally:
            os.unlink(db_path)
    
    def test_analyzer_bullish_bearish_count(self):
        """Snapshot correctly counts bullish/bearish signals."""
        prices = [2000.0 + i * 2 for i in range(60)]
        candles = make_candles(prices)
        
        # Use file-based temp database to avoid in-memory connection issues
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            repo = OHLCRepository(db_path)
            for candle in candles:
                repo.save(candle)
            
            analyzer = TechnicalAnalyzer(repo)
            snapshot = analyzer.analyze(Timeframe.H1)
            
            # Total should not exceed 4 (we have 4 indicators)
            total = snapshot.bullish_count() + snapshot.bearish_count()
            assert total <= 4
        finally:
            os.unlink(db_path)
