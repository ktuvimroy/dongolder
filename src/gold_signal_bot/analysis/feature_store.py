"""Feature engineering for ML-based pattern recognition.

This module provides the FeatureEngineer class that creates ML features
from OHLCV price data and technical indicator values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# Periods for lagged feature calculation
LOOKBACK_PERIODS = [3, 5, 10, 20]


class FeatureEngineer:
    """Create ML features from OHLCV and indicator data.
    
    Transforms raw price and indicator data into a feature matrix suitable
    for machine learning models. Generates price-based, momentum, trend,
    and volatility features.
    
    Example:
        >>> engineer = FeatureEngineer()
        >>> features = engineer.create_features(df)
        >>> target = engineer.create_target(df)
    """
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from price and indicator data.
        
        Expected input columns:
            - open, high, low, close, volume (OHLCV)
            - rsi (RSI value)
            - macd, macd_signal (MACD values)
            - ema_21, ema_50 (EMA values)
            - bb_upper, bb_lower, bb_middle (Bollinger Bands)
        
        Args:
            df: DataFrame with OHLCV and indicator columns.
            
        Returns:
            DataFrame with engineered features, NaN rows dropped.
        """
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['price_change_pct'] = df['close'].pct_change()
        features['high_low_range'] = (df['high'] - df['low']) / df['close']
        features['close_to_high'] = (df['high'] - df['close']) / df['high']
        
        # Lagged returns and volatility
        for period in LOOKBACK_PERIODS:
            features[f'return_{period}d'] = df['close'].pct_change(period)
            features[f'volatility_{period}d'] = (
                df['close'].pct_change().rolling(period).std()
            )
        
        # RSI features
        if 'rsi' in df.columns:
            features['rsi'] = df['rsi']
            features['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            features['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        
        # MACD features
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            features['macd_histogram'] = df['macd'] - df['macd_signal']
            # Crossover: detect sign changes in histogram
            hist = df['macd'] - df['macd_signal']
            features['macd_crossover'] = np.sign(hist).diff().fillna(0)
        
        # EMA features
        if 'ema_21' in df.columns and 'ema_50' in df.columns:
            features['price_vs_ema21'] = (df['close'] - df['ema_21']) / df['ema_21']
            features['price_vs_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
            features['ema_trend'] = (df['ema_21'] > df['ema_50']).astype(int)
        
        # Bollinger Bands features
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'bb_middle']):
            band_width = df['bb_upper'] - df['bb_lower']
            # Avoid division by zero
            features['bb_position'] = np.where(
                band_width > 0,
                (df['close'] - df['bb_lower']) / band_width,
                0.5
            )
            features['bb_squeeze'] = np.where(
                df['bb_middle'] > 0,
                band_width / df['bb_middle'],
                0
            )
        
        # Drop rows with NaN (due to lagged features)
        return features.dropna()
    
    def create_target(self, df: pd.DataFrame, horizon: int = 1) -> pd.Series:
        """Create classification target: did price go up or down?
        
        Args:
            df: DataFrame with 'close' column.
            horizon: Days ahead to look (default 1).
            
        Returns:
            Series with:
                1 (up >0.1%)
                -1 (down >0.1%)
                0 (flat, change <0.1%)
        """
        future_return = df['close'].shift(-horizon) / df['close'] - 1
        target = pd.Series(0, index=df.index)
        target[future_return > 0.001] = 1      # Up more than 0.1%
        target[future_return < -0.001] = -1    # Down more than 0.1%
        return target
