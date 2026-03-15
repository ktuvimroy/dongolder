"""ML-based pattern recognition for price prediction.

This module provides the PatternRecognizer class that trains machine learning
models on historical price and indicator data to predict future price direction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit

from .feature_store import FeatureEngineer
from .models import MLPrediction

if TYPE_CHECKING:
    from sklearn.ensemble import HistGradientBoostingClassifier as HGBClassifier


class PatternRecognizer:
    """ML-based pattern recognition using gradient boosting.
    
    Trains on historical price and indicator data to recognize patterns
    that precede price movements. Uses TimeSeriesSplit for temporal
    cross-validation to avoid look-ahead bias.
    
    Attributes:
        MODEL_PATH: Default path for persisted models.
        MIN_TRAINING_SAMPLES: Minimum samples required for training.
    
    Example:
        >>> engineer = FeatureEngineer()
        >>> recognizer = PatternRecognizer(engineer)
        >>> metrics = recognizer.train(df)
        >>> prediction = recognizer.predict(df)
    """
    
    MODEL_PATH = "data/models/pattern_model.joblib"
    MIN_TRAINING_SAMPLES = 100
    
    def __init__(
        self,
        feature_engineer: FeatureEngineer,
        model_path: str | None = None
    ) -> None:
        """Initialize PatternRecognizer.
        
        Args:
            feature_engineer: FeatureEngineer instance for creating features.
            model_path: Optional custom path for model persistence.
        """
        self.feature_engineer = feature_engineer
        self.model_path = model_path or self.MODEL_PATH
        self.model: HistGradientBoostingClassifier | None = None
        self._feature_names: list[str] | None = None
        self._load_model_if_exists()
    
    def train(self, df: pd.DataFrame, n_splits: int = 5) -> dict:
        """Train model on historical data with temporal cross-validation.
        
        Uses TimeSeriesSplit to ensure no look-ahead bias during validation.
        Trains final model on all available data after cross-validation.
        
        Args:
            df: DataFrame with OHLCV + indicator columns.
            n_splits: Number of TimeSeriesSplit folds (default 5).
            
        Returns:
            Dict with training metrics:
                - fold_scores: List of accuracy scores per fold
                - avg_accuracy: Mean accuracy across folds
                
        Raises:
            ValueError: If fewer than MIN_TRAINING_SAMPLES available.
        """
        features = self.feature_engineer.create_features(df)
        target = self.feature_engineer.create_target(df)
        
        # Align features and target (drop NaN rows)
        aligned = features.join(target.rename('target')).dropna()
        X = aligned.drop('target', axis=1)
        y = aligned['target']
        
        if len(X) < self.MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Need {self.MIN_TRAINING_SAMPLES}+ samples, got {len(X)}"
            )
        
        # Store feature names for later validation
        self._feature_names = list(X.columns)
        
        # TimeSeriesSplit for temporal validation (no look-ahead)
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model = HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=5,
                learning_rate=0.1,
                early_stopping=True,
                validation_fraction=0.1,
                random_state=42
            )
            model.fit(X_train, y_train)
            scores.append(model.score(X_val, y_val))
        
        # Final model on all data
        self.model = HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=5,
            learning_rate=0.1,
            early_stopping=True,
            random_state=42
        )
        self.model.fit(X, y)
        self._save_model()
        
        return {
            "fold_scores": scores,
            "avg_accuracy": sum(scores) / len(scores)
        }
    
    def predict(self, df: pd.DataFrame) -> MLPrediction | None:
        """Predict direction for the latest data row.
        
        Args:
            df: DataFrame with OHLCV + indicator columns.
                Needs at least 20 rows for feature calculation.
                
        Returns:
            MLPrediction with direction and probability, or None if:
                - Model not trained
                - Insufficient data for features
        """
        if self.model is None:
            return None
        
        features = self.feature_engineer.create_features(df)
        if features.empty:
            return None
        
        # Get latest row
        X = features.iloc[[-1]]
        pred = self.model.predict(X)[0]
        proba = self.model.predict_proba(X).max()
        
        return MLPrediction.from_prediction(int(pred), float(proba))
    
    def _save_model(self) -> None:
        """Save trained model to disk."""
        model_dir = Path(self.model_path).parent
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model and feature names together
        model_data = {
            'model': self.model,
            'feature_names': self._feature_names
        }
        joblib.dump(model_data, self.model_path)
    
    def _load_model_if_exists(self) -> None:
        """Load model from disk if exists."""
        if os.path.exists(self.model_path):
            try:
                model_data = joblib.load(self.model_path)
                if isinstance(model_data, dict):
                    self.model = model_data.get('model')
                    self._feature_names = model_data.get('feature_names')
                else:
                    # Legacy format: just the model
                    self.model = model_data
            except Exception:
                # If loading fails, start fresh
                self.model = None
    
    @property
    def is_trained(self) -> bool:
        """Check if model is trained and ready for prediction."""
        return self.model is not None
