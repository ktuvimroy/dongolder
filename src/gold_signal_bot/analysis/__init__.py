"""Technical analysis module for XAU/USD signal generation.

This module provides technical indicator calculations, support/resistance
detection, signal generation, multi-indicator fusion, and ML-based pattern
recognition.
"""

from .analyzer import TechnicalAnalyzer
from .feature_store import FeatureEngineer
from .fusion import FusionEngine, FusionResult, IndicatorWeight
from .indicators import (
    calculate_bbands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    ohlc_to_dataframe,
)
from .ml_patterns import PatternRecognizer
from .models import (
    BollingerResult,
    EMAResult,
    MACDResult,
    MLPrediction,
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
    "PatternRecognizer",
    # Feature engineering
    "FeatureEngineer",
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
    "MLPrediction",
]
