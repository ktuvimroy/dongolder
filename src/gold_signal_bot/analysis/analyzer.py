"""Technical analyzer for generating indicator snapshots.

This module provides TechnicalAnalyzer that calculates all technical
indicators for OHLC data and produces TechnicalSnapshot results.
"""

from datetime import datetime, timezone

from ..data.models import OHLC, Timeframe
from ..data.repository import OHLCRepository
from .indicators import (
    calculate_bbands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)
from .models import (
    BollingerResult,
    EMAResult,
    MACDResult,
    RSIResult,
    TechnicalSnapshot,
)


class TechnicalAnalyzer:
    """Calculates technical indicators for a given timeframe.
    
    Fetches OHLC data from repository and computes RSI, MACD, EMA,
    and Bollinger Bands indicators.
    
    Example:
        analyzer = TechnicalAnalyzer(ohlc_repo)
        snapshot = analyzer.analyze(Timeframe.H4)
        print(f"RSI: {snapshot.rsi.value}, Signal: {snapshot.rsi.signal}")
    """
    
    # Minimum candles needed for each indicator
    MIN_CANDLES_RSI = 15  # RSI(14) + 1
    MIN_CANDLES_MACD = 35  # slow(26) + signal(9)
    MIN_CANDLES_EMA = 50  # EMA(50)
    MIN_CANDLES_BBANDS = 20  # BBands(20)
    
    # Combined minimum for full analysis
    MIN_CANDLES = 50
    
    def __init__(self, ohlc_repo: OHLCRepository) -> None:
        """Initialize analyzer with OHLC repository.
        
        Args:
            ohlc_repo: Repository to fetch candle data from.
        """
        self.ohlc_repo = ohlc_repo
    
    def analyze(
        self,
        timeframe: Timeframe,
        candles: list[OHLC] | None = None
    ) -> TechnicalSnapshot:
        """Analyze technical indicators for a timeframe.
        
        Args:
            timeframe: The timeframe to analyze.
            candles: Optional pre-loaded candles. If None, fetches from repo.
            
        Returns:
            TechnicalSnapshot with all indicator results.
        """
        if candles is None:
            candles = self.ohlc_repo.get_latest(
                timeframe=timeframe,
                limit=self.MIN_CANDLES
            )
        
        if not candles:
            return TechnicalSnapshot(
                timestamp=datetime.now(timezone.utc),
                rsi=None,
                macd=None,
                ema=None,
                bollinger=None,
            )
        
        # Get current price from latest candle
        current_price = candles[-1].close
        timestamp = candles[-1].timestamp
        
        # Calculate each indicator
        rsi_result = self._calculate_rsi(candles)
        macd_result = self._calculate_macd(candles)
        ema_result = self._calculate_ema(candles, current_price)
        bollinger_result = self._calculate_bollinger(candles, current_price)
        
        return TechnicalSnapshot(
            timestamp=timestamp,
            rsi=rsi_result,
            macd=macd_result,
            ema=ema_result,
            bollinger=bollinger_result,
        )
    
    def _calculate_rsi(self, candles: list[OHLC]) -> RSIResult | None:
        """Calculate RSI indicator."""
        rsi_value = calculate_rsi(candles, period=14)
        if rsi_value is None:
            return None
        return RSIResult.from_value(rsi_value)
    
    def _calculate_macd(self, candles: list[OHLC]) -> MACDResult | None:
        """Calculate MACD indicator."""
        macd_values = calculate_macd(candles, fast=12, slow=26, signal=9)
        if macd_values is None:
            return None
        macd_line, signal_line, histogram = macd_values
        return MACDResult.from_values(macd_line, signal_line, histogram)
    
    def _calculate_ema(
        self, candles: list[OHLC], price: float
    ) -> EMAResult | None:
        """Calculate EMA indicators."""
        ema_21 = calculate_ema(candles, period=21)
        ema_50 = calculate_ema(candles, period=50)
        if ema_21 is None or ema_50 is None:
            return None
        return EMAResult.from_values(ema_21, ema_50, price)
    
    def _calculate_bollinger(
        self, candles: list[OHLC], price: float
    ) -> BollingerResult | None:
        """Calculate Bollinger Bands indicator."""
        bbands = calculate_bbands(candles, period=20, std_dev=2.0)
        if bbands is None:
            return None
        upper, middle, lower = bbands
        return BollingerResult.from_values(upper, middle, lower, price)
    
    def analyze_from_candles(
        self, candles: list[OHLC]
    ) -> TechnicalSnapshot:
        """Analyze technical indicators from provided candles.
        
        Convenience method for testing or external data sources.
        
        Args:
            candles: List of OHLC candles to analyze.
            
        Returns:
            TechnicalSnapshot with all indicator results.
        """
        if not candles:
            return TechnicalSnapshot(
                timestamp=datetime.now(timezone.utc),
                rsi=None,
                macd=None,
                ema=None,
                bollinger=None,
            )
        return self.analyze(candles[-1].timeframe, candles=candles)
