# Phase 5: Advanced Analysis - Research

**Researched:** 2026-03-15
**Domain:** News sentiment analysis, ML pattern recognition for gold trading signals
**Confidence:** MEDIUM (recommendations verified against official docs, some integration specifics need validation)

## Summary

This phase adds two advanced analysis capabilities to the gold signal bot:
1. **News Sentiment Analysis** - Factor gold-related news sentiment into trading signals
2. **ML Pattern Recognition** - Use machine learning to identify price patterns

**Key findings:**
- Alpha Vantage's built-in NEWS_SENTIMENT API is the optimal choice - already integrated, provides pre-computed sentiment scores, and supports gold/forex/commodities filtering
- TextBlob is the recommended sentiment library for any text without pre-computed scores - lightweight, offline-capable, and appropriate for financial text
- scikit-learn's HistGradientBoostingRegressor is ideal for ML - handles small datasets well, has built-in regularization/early stopping, and runs efficiently on free-tier hosting

**Primary recommendation:** Leverage Alpha Vantage's NEWS_SENTIMENT API (already integrated) as the primary news source, with TextBlob as fallback for custom sentiment analysis. Use scikit-learn for pattern recognition with engineered features from existing technical indicators.

## Standard Stack

The established libraries/tools for this domain:

### Core (News Sentiment)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Alpha Vantage NEWS_SENTIMENT | API v1 | Pre-scored news sentiment | Already integrated, includes sentiment scores, supports gold/forex/commodities filtering |
| TextBlob | >=0.18.0 | Fallback sentiment analysis | Lightweight, offline after setup, simple API, returns polarity [-1, 1] |

### Core (ML Pattern Recognition)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.4 | ML model training/prediction | HistGradientBoosting handles small data well, built-in regularization, efficient |
| pandas | >=2.0 | Feature engineering | Already in project, excellent for time-series features |
| joblib | >=1.3 | Model persistence | Bundled with scikit-learn, efficient serialization |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nltk | >=3.8 | VADER sentiment | If financial-specific sentiment needed |
| NewsAPI | Free tier | Additional news source | If Alpha Vantage rate limits exceeded |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alpha Vantage NEWS_SENTIMENT | NewsAPI + TextBlob | More API calls, no pre-computed sentiment |
| TextBlob | VADER (NLTK) | Better for social media, heavier dependency |
| HistGradientBoosting | LightGBM | Faster but adds external dependency |
| HistGradientBoosting | RandomForest | Higher variance with limited data |

**Installation:**
```bash
pip install textblob scikit-learn
python -m textblob.download_corpora lite  # Download only essential NLTK data
```

## Architecture Patterns

### Recommended Project Structure

```
src/gold_signal_bot/
├── analysis/
│   ├── sentiment.py       # SentimentAnalyzer class
│   ├── ml_patterns.py     # PatternRecognizer class  
│   ├── fusion.py          # Updated: integrate sentiment + ML
│   └── models.py          # Updated: add SentimentResult, MLPrediction
├── data/
│   ├── news_fetcher.py    # NewsFetcher class for Alpha Vantage NEWS_SENTIMENT
│   └── feature_store.py   # Feature engineering for ML
└── ml/
    └── trained_models/    # Persisted model files (.joblib)
```

### Pattern 1: Adapter Pattern for News Sources

**What:** Abstract news fetching behind a common interface to allow swapping sources
**When to use:** Multiple potential news sources (Alpha Vantage, NewsAPI, RSS)
**Example:**
```python
# Source: architecture best practice
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NewsItem:
    """Normalized news item from any source."""
    title: str
    summary: str
    published: datetime
    source: str
    sentiment_score: float | None = None  # Pre-computed if available
    relevance_score: float | None = None

class NewsSource(ABC):
    @abstractmethod
    async def fetch_gold_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch gold-related news items."""
        pass

class AlphaVantageNews(NewsSource):
    """Alpha Vantage NEWS_SENTIMENT as primary source."""
    
    async def fetch_gold_news(self, limit: int = 50) -> list[NewsItem]:
        # Use topics=financial_markets,commodities and tickers for gold
        url = f"{self.base_url}/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "topics": "financial_markets,economy_monetary",
            "tickers": "FOREX:XAU",  # Gold forex ticker
            "limit": limit,
            "apikey": self.api_key
        }
        # Parse response into NewsItem objects
        ...
```

### Pattern 2: Feature Engineering Pipeline

**What:** Systematic feature creation from price/indicator data for ML
**When to use:** Training and prediction time
**Example:**
```python
# Source: scikit-learn time-series patterns
import pandas as pd
import numpy as np

class FeatureEngineer:
    """Create ML features from price and indicator data."""
    
    LOOKBACK_PERIODS = [3, 5, 10, 20]  # Days to look back
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from OHLCV and indicator data.
        
        Input columns: open, high, low, close, volume,
                       rsi, macd, macd_signal, ema_21, ema_50, 
                       bb_upper, bb_lower, bb_middle
        """
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['price_change_pct'] = df['close'].pct_change()
        features['high_low_range'] = (df['high'] - df['low']) / df['close']
        features['close_to_high'] = (df['high'] - df['close']) / df['high']
        
        # Lagged returns (momentum)
        for period in self.LOOKBACK_PERIODS:
            features[f'return_{period}d'] = df['close'].pct_change(period)
            features[f'volatility_{period}d'] = df['close'].pct_change().rolling(period).std()
        
        # Technical indicator values (already available)
        features['rsi'] = df['rsi']
        features['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        features['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        
        features['macd_histogram'] = df['macd'] - df['macd_signal']
        features['macd_crossover'] = np.sign(features['macd_histogram']).diff()
        
        features['price_vs_ema21'] = (df['close'] - df['ema_21']) / df['ema_21']
        features['price_vs_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
        features['ema_trend'] = (df['ema_21'] > df['ema_50']).astype(int)
        
        # Bollinger Band position
        bb_width = df['bb_upper'] - df['bb_lower']
        features['bb_position'] = (df['close'] - df['bb_lower']) / bb_width
        features['bb_squeeze'] = bb_width / df['bb_middle']
        
        return features.dropna()
```

### Pattern 3: Weighted Signal Integration

**What:** Combine sentiment and ML predictions with existing technical signals
**When to use:** Final signal generation in FusionEngine
**Example:**
```python
# Source: Extension of existing FusionEngine pattern
@dataclass
class EnhancedIndicatorWeight:
    """Weights for all signal sources."""
    # Technical indicators (existing)
    rsi: float = 0.20
    macd: float = 0.25
    ema: float = 0.20
    bollinger: float = 0.15
    # New sources
    sentiment: float = 0.10  # News sentiment adjustment
    ml_pattern: float = 0.10  # ML pattern recognition
    
class EnhancedFusionEngine(FusionEngine):
    """Extended fusion with sentiment and ML signals."""
    
    def fuse_with_advanced(
        self,
        snapshot: TechnicalSnapshot,
        current_price: float,
        sentiment_result: SentimentResult | None = None,
        ml_prediction: MLPrediction | None = None,
        support: PriceLevel | None = None,
        resistance: PriceLevel | None = None,
    ) -> FusionResult:
        # Get base technical fusion
        result = self.fuse(snapshot, current_price, support, resistance)
        
        # Apply sentiment adjustment (±10% max)
        if sentiment_result and sentiment_result.confidence > 0.5:
            sentiment_adj = sentiment_result.score * self.weights.sentiment
            if sentiment_result.score > 0:
                result.bullish_score += sentiment_adj
            else:
                result.bearish_score += abs(sentiment_adj)
        
        # Apply ML prediction adjustment (±10% max)
        if ml_prediction and ml_prediction.confidence > 0.6:
            ml_adj = ml_prediction.strength * self.weights.ml_pattern
            if ml_prediction.direction == SignalDirection.BULLISH:
                result.bullish_score += ml_adj
            elif ml_prediction.direction == SignalDirection.BEARISH:
                result.bearish_score += ml_adj
        
        # Recalculate final direction
        result = self._recalculate_direction(result)
        return result
```

### Anti-Patterns to Avoid

- **Over-relying on ML predictions:** ML should supplement, not replace technical analysis. Keep ML weight at 10-15% max
- **Using raw sentiment values:** Always normalize sentiment to [-1, 1] range before integration
- **Training on too little data:** Need minimum 6 months of historical data for meaningful patterns
- **Ignoring feature importance:** Regularly check which features the ML model actually uses
- **Complex neural networks:** Stick to gradient boosting for this data size; neural nets need much more data

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sentiment scoring | Custom word lists | TextBlob or Alpha Vantage | Pre-trained, handles negation/intensifiers |
| Gradient boosting | Custom implementation | scikit-learn HistGradientBoosting | Highly optimized, handles edge cases |
| Feature scaling | Manual normalization | sklearn StandardScaler/MinMaxScaler | Handles edge cases, fits training data |
| Cross-validation | Manual train/test splits | sklearn TimeSeriesSplit | Proper temporal ordering for time series |
| Model persistence | pickle | joblib | Efficiently handles numpy arrays |

**Key insight:** Financial ML requires proper temporal handling. Using random train/test splits will cause data leakage and overfit models.

## Common Pitfalls

### Pitfall 1: Look-Ahead Bias in Feature Engineering

**What goes wrong:** Using future data to create features (e.g., using today's close to predict today's direction)
**Why it happens:** Easy to accidentally include current-period data in features
**How to avoid:** Always use `.shift(1)` for target variables; features should only use data available at prediction time
**Warning signs:** Unrealistically high backtest accuracy (>80%)

### Pitfall 2: Alpha Vantage Rate Limiting

**What goes wrong:** Hitting 25 calls/day limit, causing missing data
**Why it happens:** Multiple API calls for price + news + indicators
**How to avoid:** 
- Cache news responses (news doesn't change retroactively)
- Batch multiple ticker lookups
- Use SQLite to store fetched news
- Schedule news fetch once per hour, not per analysis
**Warning signs:** HTTP 429 errors, empty API responses

### Pitfall 3: Sentiment Lag vs Price Reaction

**What goes wrong:** News sentiment already priced in by the time you see it
**Why it happens:** Gold prices react to news within minutes
**How to avoid:**
- Use sentiment as confirmation, not primary signal
- Weight recent news (< 4 hours) higher than older news
- Focus on sentiment trend changes, not absolute values
**Warning signs:** Sentiment and price moving opposite directions

### Pitfall 4: Overfitting with Limited Historical Data

**What goes wrong:** ML model memorizes training data, poor generalization
**Why it happens:** Too many features relative to samples, no regularization
**How to avoid:**
- Use strong regularization (`l2_regularization=0.1` or higher)
- Enable early stopping (`early_stopping=True`)
- Keep features under 20
- Use TimeSeriesSplit with at least 5 folds
- Validate on out-of-sample period (last 2 months)
**Warning signs:** Training accuracy >> validation accuracy

### Pitfall 5: TextBlob NLTK Data Not Downloaded

**What goes wrong:** TextBlob throws error about missing corpora
**Why it happens:** NLTK data must be downloaded separately
**How to avoid:**
```python
# In setup/init code:
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
```
**Warning signs:** `LookupError: Resource punkt not found`

## Code Examples

Verified patterns from official sources:

### Alpha Vantage NEWS_SENTIMENT Request

```python
# Source: Alpha Vantage official documentation
import aiohttp
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GoldNewsItem:
    title: str
    summary: str
    published: datetime
    overall_sentiment_score: float  # -1 to 1
    overall_sentiment_label: str    # Bearish/Neutral/Bullish
    relevance_score: float          # 0 to 1

async def fetch_gold_news(api_key: str) -> list[GoldNewsItem]:
    """Fetch gold-related news with pre-computed sentiment."""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": "financial_markets,economy_monetary",
        "tickers": "FOREX:XAU",  # Gold
        "sort": "LATEST",
        "limit": 50,
        "apikey": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
    
    items = []
    for article in data.get("feed", []):
        items.append(GoldNewsItem(
            title=article["title"],
            summary=article.get("summary", ""),
            published=datetime.strptime(
                article["time_published"], 
                "%Y%m%dT%H%M%S"
            ),
            overall_sentiment_score=float(article["overall_sentiment_score"]),
            overall_sentiment_label=article["overall_sentiment_label"],
            relevance_score=float(article.get("relevance_score", 0.5))
        ))
    return items
```

### TextBlob Sentiment Analysis

```python
# Source: TextBlob official quickstart
from textblob import TextBlob
from dataclasses import dataclass

@dataclass
class SentimentResult:
    polarity: float      # -1.0 to 1.0 (negative to positive)
    subjectivity: float  # 0.0 to 1.0 (objective to subjective)
    
    @property
    def score(self) -> float:
        """Weighted score favoring objective sentiment."""
        # More objective = more trustworthy for trading
        objectivity_weight = 1.0 - self.subjectivity
        return self.polarity * (0.5 + 0.5 * objectivity_weight)

def analyze_sentiment(text: str) -> SentimentResult:
    """Analyze sentiment of text using TextBlob."""
    blob = TextBlob(text)
    return SentimentResult(
        polarity=blob.sentiment.polarity,
        subjectivity=blob.sentiment.subjectivity
    )

def aggregate_news_sentiment(news_items: list[GoldNewsItem]) -> SentimentResult:
    """Aggregate sentiment from multiple news items."""
    if not news_items:
        return SentimentResult(polarity=0.0, subjectivity=0.5)
    
    # Weight by recency and relevance
    total_weight = 0.0
    weighted_polarity = 0.0
    weighted_subjectivity = 0.0
    
    for item in news_items:
        # Use pre-computed score from Alpha Vantage
        weight = item.relevance_score
        weighted_polarity += item.overall_sentiment_score * weight
        weighted_subjectivity += 0.5  # Assume moderate subjectivity for news
        total_weight += weight
    
    if total_weight == 0:
        return SentimentResult(polarity=0.0, subjectivity=0.5)
    
    return SentimentResult(
        polarity=weighted_polarity / total_weight,
        subjectivity=weighted_subjectivity / total_weight
    )
```

### scikit-learn HistGradientBoosting for Pattern Recognition

```python
# Source: scikit-learn official ensemble documentation
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report
import pandas as pd
import numpy as np
import joblib

class GoldPatternRecognizer:
    """ML-based pattern recognition for gold price movements."""
    
    def __init__(self):
        self.model = HistGradientBoostingClassifier(
            max_iter=100,
            learning_rate=0.1,
            max_depth=5,
            min_samples_leaf=20,
            l2_regularization=0.1,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=10,
            random_state=42
        )
        self.feature_columns: list[str] = []
        
    def prepare_target(self, df: pd.DataFrame, lookahead: int = 1) -> pd.Series:
        """Create classification target: 1=bullish, 0=neutral, -1=bearish.
        
        Bullish: Next day close > today's close + 0.3%
        Bearish: Next day close < today's close - 0.3%
        Neutral: Within ±0.3%
        """
        future_return = df['close'].pct_change(lookahead).shift(-lookahead)
        
        target = pd.Series(0, index=df.index)  # Default neutral
        target[future_return > 0.003] = 1      # Bullish
        target[future_return < -0.003] = -1    # Bearish
        
        return target
    
    def train(self, features: pd.DataFrame, target: pd.Series) -> dict:
        """Train model with time-series cross-validation."""
        # Store feature names for validation
        self.feature_columns = features.columns.tolist()
        
        # Drop any rows with NaN
        mask = ~(features.isna().any(axis=1) | target.isna())
        X = features[mask].values
        y = target[mask].values
        
        # Time-series split (no shuffling!)
        tscv = TimeSeriesSplit(n_splits=5, test_size=20)
        
        scores = []
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            self.model.fit(X_train, y_train)
            scores.append(self.model.score(X_test, y_test))
        
        # Final fit on all data
        self.model.fit(X, y)
        
        return {
            "cv_scores": scores,
            "mean_accuracy": np.mean(scores),
            "std_accuracy": np.std(scores),
            "n_iter": self.model.n_iter_
        }
    
    def predict(self, features: pd.DataFrame) -> tuple[int, float]:
        """Predict direction and confidence.
        
        Returns:
            (direction, confidence): direction in {-1, 0, 1}, confidence in [0, 1]
        """
        if not self.feature_columns:
            raise ValueError("Model not trained yet")
        
        # Ensure same features
        X = features[self.feature_columns].values.reshape(1, -1)
        
        direction = self.model.predict(X)[0]
        probas = self.model.predict_proba(X)[0]
        confidence = max(probas)  # Confidence is max class probability
        
        return int(direction), float(confidence)
    
    def save(self, path: str):
        """Persist trained model."""
        joblib.dump({
            'model': self.model,
            'feature_columns': self.feature_columns
        }, path)
    
    def load(self, path: str):
        """Load trained model."""
        data = joblib.load(path)
        self.model = data['model']
        self.feature_columns = data['feature_columns']
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual sentiment lexicons | Pre-trained transformers | 2020+ | Better accuracy but heavier |
| LSTM for time series | Gradient Boosting (tabular) | 2022+ | Better for small data, easier to deploy |
| Random train/test split | TimeSeriesSplit | Always best practice | Prevents look-ahead bias |
| News scraping | API with pre-computed scores | 2023+ | Alpha Vantage NEWS_SENTIMENT simplifies pipeline |

**Deprecated/outdated:**
- Using stock-focused news APIs for gold (gold trades as FOREX:XAU or commodity)
- Training deep learning on < 1 year of daily data
- Real-time sentiment (too slow to react vs algorithmic traders)

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal sentiment window**
   - What we know: More recent news is more relevant
   - What's unclear: Exact decay function (linear? exponential?) for weighting older news
   - Recommendation: Start with exponential decay, half-life of 4 hours

2. **ML model retraining frequency**
   - What we know: Markets change, models drift
   - What's unclear: How often to retrain for gold specifically
   - Recommendation: Monthly retraining with rolling 6-month window

3. **Alpha Vantage topic combination**
   - What we know: Can combine topics (financial_markets + economy_monetary)
   - What's unclear: Whether FOREX:XAU ticker filter works reliably for gold news
   - Recommendation: Test in development; may need "gold" keyword fallback

## Sources

### Primary (HIGH confidence)

- Alpha Vantage NEWS_SENTIMENT API documentation - https://www.alphavantage.co/documentation/#news-sentiment
- scikit-learn Ensemble methods documentation - https://scikit-learn.org/stable/modules/ensemble.html
- TextBlob Quickstart - https://textblob.readthedocs.io/en/dev/quickstart.html

### Secondary (MEDIUM confidence)

- Finnhub Market News API - https://finnhub.io/docs/api/market-news
- NewsAPI Documentation - https://newsapi.org/docs/get-started

### Tertiary (LOW confidence)

- General ML for trading patterns (needs validation with gold-specific data)
- Sentiment-price correlation (varies by market conditions)

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Alpha Vantage NEWS_SENTIMENT not tested with gold specifically
- Architecture: HIGH - Patterns follow existing codebase structure
- Pitfalls: HIGH - Common issues verified across multiple sources

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (30 days - stable domain)

---

## Integration Points with Existing Code

### Files to Modify

| File | Change | Reason |
|------|--------|--------|
| `analysis/models.py` | Add `SentimentResult`, `MLPrediction` dataclasses | New data models |
| `analysis/fusion.py` | Extend `FusionEngine` with `fuse_with_advanced()` | Integrate new signals |
| `data/fetcher.py` | Add `fetch_gold_news()` method | Reuse Alpha Vantage client |
| `pyproject.toml` | Add `textblob`, `scikit-learn` dependencies | New libraries |

### Files to Create

| File | Purpose |
|------|---------|
| `analysis/sentiment.py` | `SentimentAnalyzer` class |
| `analysis/ml_patterns.py` | `PatternRecognizer` class |
| `data/feature_store.py` | `FeatureEngineer` class |

### Configuration Additions

```python
# In config.py
class AdvancedAnalysisSettings(BaseSettings):
    """Settings for advanced analysis features."""
    
    # Sentiment
    sentiment_weight: float = 0.10
    sentiment_min_confidence: float = 0.5
    news_lookback_hours: int = 24
    
    # ML
    ml_weight: float = 0.10
    ml_min_confidence: float = 0.6
    ml_retrain_days: int = 30
    ml_training_months: int = 6
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alpha Vantage rate limit exceeded | MEDIUM | Signal gaps | Cache news, schedule fetches |
| ML model overfitting | MEDIUM | Poor predictions | Strong regularization, validation |
| Sentiment lagging price | HIGH | Reduced signal value | Use as confirmation only, low weight |
| TextBlob inaccurate on financial text | LOW | Wrong sentiment | Alpha Vantage pre-scored is primary |
| Model drift over time | MEDIUM | Degraded accuracy | Monthly retraining schedule |
