"""Tests for ML-based pattern recognition.

Tests cover feature engineering, target creation, model training,
prediction, and model persistence.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gold_signal_bot.analysis.feature_store import FeatureEngineer, LOOKBACK_PERIODS
from gold_signal_bot.analysis.ml_patterns import PatternRecognizer
from gold_signal_bot.analysis.models import MLPrediction, SignalDirection


def create_synthetic_ohlcv(n_rows: int = 200) -> pd.DataFrame:
    """Create synthetic OHLCV data with indicator columns for testing.
    
    Args:
        n_rows: Number of rows to generate.
        
    Returns:
        DataFrame with OHLCV and indicator columns.
    """
    np.random.seed(42)
    close = 2650 + np.cumsum(np.random.randn(n_rows) * 5)
    return pd.DataFrame({
        'open': close - np.random.rand(n_rows) * 2,
        'high': close + np.random.rand(n_rows) * 5,
        'low': close - np.random.rand(n_rows) * 5,
        'close': close,
        'volume': np.random.randint(1000, 10000, n_rows),
        'rsi': np.random.uniform(20, 80, n_rows),
        'macd': np.random.randn(n_rows),
        'macd_signal': np.random.randn(n_rows),
        'ema_21': close - np.random.randn(n_rows) * 3,
        'ema_50': close - np.random.randn(n_rows) * 5,
        'bb_upper': close + 20,
        'bb_lower': close - 20,
        'bb_middle': close,
    })


class TestFeatureEngineer:
    """Tests for FeatureEngineer class."""
    
    def test_create_features_returns_expected_columns(self):
        """create_features() should produce 15+ features."""
        df = create_synthetic_ohlcv(100)
        engineer = FeatureEngineer()
        features = engineer.create_features(df)
        
        # Should have at least 15 feature columns
        assert len(features.columns) >= 15
        
        # Check key feature categories exist
        assert 'price_change_pct' in features.columns
        assert 'rsi' in features.columns
        assert 'macd_histogram' in features.columns
        assert 'ema_trend' in features.columns
        assert 'bb_position' in features.columns
    
    def test_create_features_includes_lagged_returns(self):
        """create_features() should create lagged return features."""
        df = create_synthetic_ohlcv(100)
        engineer = FeatureEngineer()
        features = engineer.create_features(df)
        
        for period in LOOKBACK_PERIODS:
            assert f'return_{period}d' in features.columns
            assert f'volatility_{period}d' in features.columns
    
    def test_create_features_drops_nan_rows(self):
        """create_features() should drop NaN rows."""
        df = create_synthetic_ohlcv(100)
        engineer = FeatureEngineer()
        features = engineer.create_features(df)
        
        # No NaN values should remain
        assert not features.isna().any().any()
        
        # Some rows should be dropped (due to lagged features)
        assert len(features) < len(df)
    
    def test_create_target_up_movement(self):
        """create_target() returns 1 for price increase > 0.1%."""
        df = pd.DataFrame({
            'close': [100.0, 101.0]  # 1% increase
        })
        engineer = FeatureEngineer()
        target = engineer.create_target(df, horizon=1)
        
        assert target.iloc[0] == 1  # Up
    
    def test_create_target_down_movement(self):
        """create_target() returns -1 for price decrease > 0.1%."""
        df = pd.DataFrame({
            'close': [100.0, 99.0]  # 1% decrease
        })
        engineer = FeatureEngineer()
        target = engineer.create_target(df, horizon=1)
        
        assert target.iloc[0] == -1  # Down
    
    def test_create_target_flat_movement(self):
        """create_target() returns 0 for price change < 0.1%."""
        df = pd.DataFrame({
            'close': [100.0, 100.05]  # 0.05% increase (flat)
        })
        engineer = FeatureEngineer()
        target = engineer.create_target(df, horizon=1)
        
        assert target.iloc[0] == 0  # Flat


class TestMLPrediction:
    """Tests for MLPrediction dataclass."""
    
    def test_from_prediction_bullish(self):
        """from_prediction(1, ...) returns BULLISH direction."""
        pred = MLPrediction.from_prediction(1, 0.75)
        
        assert pred.direction == SignalDirection.BULLISH
        assert pred.signal == SignalDirection.BULLISH
        assert pred.probability == 0.75
    
    def test_from_prediction_bearish(self):
        """from_prediction(-1, ...) returns BEARISH direction."""
        pred = MLPrediction.from_prediction(-1, 0.8)
        
        assert pred.direction == SignalDirection.BEARISH
        assert pred.signal == SignalDirection.BEARISH
        assert pred.probability == 0.8
    
    def test_from_prediction_neutral(self):
        """from_prediction(0, ...) returns NEUTRAL direction."""
        pred = MLPrediction.from_prediction(0, 0.5)
        
        assert pred.direction == SignalDirection.NEUTRAL
        assert pred.signal == SignalDirection.NEUTRAL
        assert pred.probability == 0.5


class TestPatternRecognizer:
    """Tests for PatternRecognizer class."""
    
    @pytest.fixture
    def temp_model_path(self, tmp_path):
        """Provide temporary path for model files."""
        return str(tmp_path / "test_model.joblib")
    
    @pytest.fixture
    def engineer(self):
        """Provide FeatureEngineer instance."""
        return FeatureEngineer()
    
    def test_train_requires_minimum_samples(self, engineer, temp_model_path):
        """train() raises ValueError with insufficient samples."""
        df = create_synthetic_ohlcv(50)  # Too few samples
        recognizer = PatternRecognizer(engineer, temp_model_path)
        
        with pytest.raises(ValueError, match="Need 100\\+ samples"):
            recognizer.train(df, n_splits=3)
    
    def test_train_returns_metrics(self, engineer, temp_model_path):
        """train() returns fold_scores and avg_accuracy."""
        df = create_synthetic_ohlcv(200)
        recognizer = PatternRecognizer(engineer, temp_model_path)
        
        metrics = recognizer.train(df, n_splits=3)
        
        assert "fold_scores" in metrics
        assert "avg_accuracy" in metrics
        assert len(metrics["fold_scores"]) == 3
        assert 0 <= metrics["avg_accuracy"] <= 1
    
    def test_train_saves_model(self, engineer, temp_model_path):
        """train() saves model to disk."""
        df = create_synthetic_ohlcv(200)
        recognizer = PatternRecognizer(engineer, temp_model_path)
        
        recognizer.train(df, n_splits=3)
        
        assert Path(temp_model_path).exists()
    
    def test_predict_returns_none_without_model(self, engineer, temp_model_path):
        """predict() returns None if model not trained."""
        df = create_synthetic_ohlcv(100)
        recognizer = PatternRecognizer(engineer, temp_model_path)
        
        result = recognizer.predict(df)
        
        assert result is None
    
    def test_predict_returns_ml_prediction(self, engineer, temp_model_path):
        """predict() returns MLPrediction after training."""
        df = create_synthetic_ohlcv(200)
        recognizer = PatternRecognizer(engineer, temp_model_path)
        recognizer.train(df, n_splits=3)
        
        result = recognizer.predict(df)
        
        assert isinstance(result, MLPrediction)
        assert result.direction in [
            SignalDirection.BULLISH,
            SignalDirection.BEARISH,
            SignalDirection.NEUTRAL
        ]
        assert 0 <= result.probability <= 1
    
    def test_model_persistence(self, engineer, temp_model_path):
        """Model loads correctly from persisted file."""
        df = create_synthetic_ohlcv(200)
        
        # Train and save
        recognizer1 = PatternRecognizer(engineer, temp_model_path)
        recognizer1.train(df, n_splits=3)
        
        # Load in new instance
        recognizer2 = PatternRecognizer(engineer, temp_model_path)
        
        assert recognizer2.is_trained
        result = recognizer2.predict(df)
        assert isinstance(result, MLPrediction)
    
    def test_is_trained_property(self, engineer, temp_model_path):
        """is_trained property reflects model state."""
        df = create_synthetic_ohlcv(200)
        recognizer = PatternRecognizer(engineer, temp_model_path)
        
        assert not recognizer.is_trained
        
        recognizer.train(df, n_splits=3)
        
        assert recognizer.is_trained
