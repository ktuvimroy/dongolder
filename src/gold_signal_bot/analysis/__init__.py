"""Technical analysis module for XAU/USD signal generation.

This module provides technical indicator calculations and analysis.
"""

from .analyzer import TechnicalAnalyzer
from .indicators import (
    calculate_bbands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    ohlc_to_dataframe,
)
from .models import (
    BollingerResult,
    EMAResult,
    MACDResult,
    RSIResult,
    SignalDirection,
    TechnicalSnapshot,
)

__all__ = [
    # Analyzer
    "TechnicalAnalyzer",
    # Indicator functions
    "calculate_rsi",
    "calculate_macd",
    "calculate_ema",
    "calculate_bbands",
    "ohlc_to_dataframe",
    # Models
    "SignalDirection",
    "RSIResult",
    "MACDResult",
    "EMAResult",
    "BollingerResult",
    "TechnicalSnapshot",
]
