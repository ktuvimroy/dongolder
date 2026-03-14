"""Technical indicator calculations using pandas-ta.

This module provides functions to calculate RSI, MACD, EMA,
and Bollinger Bands from OHLC candle data.
"""

import pandas as pd
import pandas_ta as ta

from ..data.models import OHLC


def ohlc_to_dataframe(candles: list[OHLC]) -> pd.DataFrame:
    """Convert OHLC candles to pandas DataFrame.
    
    Args:
        candles: List of OHLC candles, must be sorted by timestamp ascending.
        
    Returns:
        DataFrame with columns: timestamp, open, high, low, close
    """
    if not candles:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
    
    data = {
        "timestamp": [c.timestamp for c in candles],
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


def calculate_rsi(candles: list[OHLC], period: int = 14) -> float | None:
    """Calculate RSI (Relative Strength Index).
    
    Args:
        candles: List of OHLC candles (need at least period+1 candles).
        period: RSI period (default 14).
        
    Returns:
        RSI value (0-100) or None if insufficient data.
    """
    if len(candles) < period + 1:
        return None
    
    df = ohlc_to_dataframe(candles)
    rsi = ta.rsi(df["close"], length=period)
    
    if rsi is None or rsi.empty or pd.isna(rsi.iloc[-1]):
        return None
    
    return float(rsi.iloc[-1])


def calculate_macd(
    candles: list[OHLC],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> tuple[float, float, float] | None:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        candles: List of OHLC candles (need at least slow+signal candles).
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line period (default 9).
        
    Returns:
        Tuple of (macd_line, signal_line, histogram) or None if insufficient data.
    """
    min_required = slow + signal
    if len(candles) < min_required:
        return None
    
    df = ohlc_to_dataframe(candles)
    macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    
    if macd_df is None or macd_df.empty:
        return None
    
    # pandas-ta returns columns like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    hist_col = f"MACDh_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    
    if macd_col not in macd_df.columns:
        return None
    
    macd_val = macd_df[macd_col].iloc[-1]
    signal_val = macd_df[signal_col].iloc[-1]
    hist_val = macd_df[hist_col].iloc[-1]
    
    if pd.isna(macd_val) or pd.isna(signal_val) or pd.isna(hist_val):
        return None
    
    return (float(macd_val), float(signal_val), float(hist_val))


def calculate_ema(candles: list[OHLC], period: int) -> float | None:
    """Calculate EMA (Exponential Moving Average).
    
    Args:
        candles: List of OHLC candles.
        period: EMA period.
        
    Returns:
        EMA value or None if insufficient data.
    """
    if len(candles) < period:
        return None
    
    df = ohlc_to_dataframe(candles)
    ema = ta.ema(df["close"], length=period)
    
    if ema is None or ema.empty or pd.isna(ema.iloc[-1]):
        return None
    
    return float(ema.iloc[-1])


def calculate_bbands(
    candles: list[OHLC],
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[float, float, float] | None:
    """Calculate Bollinger Bands.
    
    Args:
        candles: List of OHLC candles (need at least period candles).
        period: MA period for middle band (default 20).
        std_dev: Standard deviation multiplier (default 2.0).
        
    Returns:
        Tuple of (upper, middle, lower) band values or None if insufficient data.
    """
    if len(candles) < period:
        return None
    
    df = ohlc_to_dataframe(candles)
    bbands = ta.bbands(df["close"], length=period, std=std_dev)
    
    if bbands is None or bbands.empty:
        return None
    
    # pandas-ta column naming may vary by version
    # Try common patterns: BBL_20_2.0 or BBL_20_2.0_2.0
    lower_col = None
    middle_col = None
    upper_col = None
    
    for col in bbands.columns:
        if col.startswith("BBL_"):
            lower_col = col
        elif col.startswith("BBM_"):
            middle_col = col
        elif col.startswith("BBU_"):
            upper_col = col
    
    if lower_col is None or middle_col is None or upper_col is None:
        return None
    
    upper = bbands[upper_col].iloc[-1]
    middle = bbands[middle_col].iloc[-1]
    lower = bbands[lower_col].iloc[-1]
    
    if pd.isna(upper) or pd.isna(middle) or pd.isna(lower):
        return None
    
    return (float(upper), float(middle), float(lower))
