"""Technical analysis module for XAU/USD signal generation.

This module provides technical indicator calculations, support/resistance
detection, signal generation, and multi-indicator fusion.
"""

from .analyzer import TechnicalAnalyzer
from .fusion import FusionEngine, FusionResult, IndicatorWeight
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
    PriceLevel,
    RawSignal,
    RSIResult,
    SignalDirection,
    TechnicalSnapshot,
)
from .signals import SignalGenerator
from .support_resistance import SupportResistanceDetector

__all__ = [
    # Analyzers
    "TechnicalAnalyzer",
    "SignalGenerator",
    "SupportResistanceDetector",
    "FusionEngine",
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
    "PriceLevel",
    "RawSignal",
    "IndicatorWeight",
    "FusionResult",
]
