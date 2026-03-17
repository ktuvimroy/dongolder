"""Tests for sentiment analysis module."""

import asyncio
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from textblob import TextBlob

from gold_signal_bot.analysis.models import SentimentResult, SignalDirection
from gold_signal_bot.analysis.sentiment import SentimentAnalyzer
from gold_signal_bot.data.news_fetcher import NewsItem


class TestSentimentResult:
    """Tests for SentimentResult dataclass and factory method."""
    
    def test_from_score_bullish(self):
        """Test from_score creates BULLISH when score > 0.1."""
        result = SentimentResult.from_score(0.5, 10)
        assert result.score == 0.5
        assert result.article_count == 10
        assert result.signal == SignalDirection.BULLISH
    
    def test_from_score_bearish(self):
        """Test from_score creates BEARISH when score < -0.1."""
        result = SentimentResult.from_score(-0.6, 8)
        assert result.score == -0.6
        assert result.article_count == 8
        assert result.signal == SignalDirection.BEARISH
    
    def test_from_score_neutral_positive_edge(self):
        """Test from_score creates NEUTRAL at positive edge."""
        result = SentimentResult.from_score(0.1, 5)
        assert result.score == 0.1
        assert result.signal == SignalDirection.NEUTRAL
    
    def test_from_score_neutral_negative_edge(self):
        """Test from_score creates NEUTRAL at negative edge."""
        result = SentimentResult.from_score(-0.1, 5)
        assert result.score == -0.1
        assert result.signal == SignalDirection.NEUTRAL
    
    def test_from_score_neutral_zero(self):
        """Test from_score creates NEUTRAL at zero."""
        result = SentimentResult.from_score(0.0, 3)
        assert result.score == 0.0
        assert result.signal == SignalDirection.NEUTRAL


class TestSentimentAnalyzerTextBlob:
    """Tests for TextBlob fallback sentiment analysis."""
    
    def test_analyze_text_positive(self):
        """Test TextBlob analysis for positive sentiment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            # Use known positive phrases
            text = "Gold prices surge and investors rejoice with strong gains"
            score = analyzer._analyze_text(text)
            
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0
            assert score > 0  # Should be positive
    
    def test_analyze_text_negative(self):
        """Test TextBlob analysis for negative sentiment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            # Use known negative phrases
            text = "Gold prices crash and investors face heavy losses"
            score = analyzer._analyze_text(text)
            
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0
            assert score < 0  # Should be negative
    
    def test_analyze_text_neutral(self):
        """Test TextBlob analysis for neutral sentiment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            # Neutral technical text
            text = "Gold trading at current levels"
            score = analyzer._analyze_text(text)
            
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0
            # Should be close to zero but we don't assert exact value
    
    def test_analyze_text_empty(self):
        """Test TextBlob analysis with empty text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            score = analyzer._analyze_text("")
            
            assert score == 0.0


class TestSentimentAnalyzerCaching:
    """Tests for sentiment result caching."""
    
    def test_init_creates_cache_db(self):
        """Test __init__ creates cache database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.db"
            
            analyzer = SentimentAnalyzer(Mock(), cache_db=str(cache_path))
            
            assert cache_path.exists()
    
    def test_cache_table_created(self):
        """Test sentiment_cache table is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.db"
            
            analyzer = SentimentAnalyzer(Mock(), cache_db=str(cache_path))
            
            conn = sqlite3.connect(str(cache_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentiment_cache'")
            result = cursor.fetchone()
            
            assert result is not None
            conn.close()
    
    def test_save_to_cache(self):
        """Test saving sentiment to cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            analyzer._save_to_cache(0.75, 15)
            
            cached = analyzer._get_cached_result()
            assert cached is not None
            assert cached.score == 0.75
            assert cached.article_count == 15
            assert cached.signal == SignalDirection.BULLISH
    
    def test_get_cached_result_within_ttl(self):
        """Test retrieving cached result within TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            analyzer._save_to_cache(0.3, 8)
            
            cached = analyzer._get_cached_result()
            
            assert cached is not None
            assert cached.score == 0.3
            assert cached.article_count == 8
    
    def test_get_cached_result_none_if_empty(self):
        """Test _get_cached_result returns None for empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(Mock(), cache_db=cache_path)
            
            cached = analyzer._get_cached_result()
            
            assert cached is None


class TestSentimentAnalyzerIntegration:
    """Integration tests for SentimentAnalyzer with mocked NewsFetcher."""
    
    @pytest.mark.asyncio
    async def test_analyze_with_pre_computed_scores(self):
        """Test analyze() uses pre-computed sentiment scores when available."""
        mock_fetcher = AsyncMock()
        
        # Create news items with pre-computed scores
        news_items = [
            NewsItem(
                title="Gold rises",
                summary="Gold price increased",
                published=datetime.now(timezone.utc),
                source="Reuters",
                sentiment_score=0.7,
                relevance_score=0.9,
                url="https://example.com/1"
            ),
            NewsItem(
                title="Gold stable",
                summary="Gold price remains stable",
                published=datetime.now(timezone.utc),
                source="Bloomberg",
                sentiment_score=0.1,
                relevance_score=0.8,
                url="https://example.com/2"
            ),
        ]
        
        mock_fetcher.fetch_gold_news.return_value = news_items
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            result = await analyzer.analyze()
            
            assert result is not None
            assert isinstance(result, SentimentResult)
            assert -1.0 <= result.score <= 1.0
            assert result.article_count == 2
            # Average should be weighted: (0.7*0.9 + 0.1*0.8) / (0.9+0.8) ≈ 0.4
            assert result.score > 0  # Positive average
            assert result.signal == SignalDirection.BULLISH
    
    @pytest.mark.asyncio
    async def test_analyze_with_textblob_fallback(self):
        """Test analyze() uses TextBlob when pre-computed scores unavailable."""
        mock_fetcher = AsyncMock()
        
        # Create news items without pre-computed scores
        # Use strongly positive text to ensure TextBlob detects it
        news_items = [
            NewsItem(
                title="Gold prices excellent",
                summary="Excellent gains as investors buy gold",
                published=datetime.now(timezone.utc),
                source="Reuters",
                sentiment_score=None,
                relevance_score=0.8,
                url="https://example.com/1"
            ),
        ]
        
        mock_fetcher.fetch_gold_news.return_value = news_items
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            result = await analyzer.analyze()
            
            assert result is not None
            assert result.article_count == 1
            # TextBlob should detect sentiment from the text
            # The exact value depends on TextBlob's lexicon, so we just verify it's computed
            assert -1.0 <= result.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_returns_neutral_on_no_news(self):
        """Test analyze() returns neutral sentiment when no news available."""
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_gold_news.return_value = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            result = await analyzer.analyze()
            
            assert result is not None
            assert result.score == 0.0
            assert result.article_count == 0
            assert result.signal == SignalDirection.NEUTRAL
    
    @pytest.mark.asyncio
    async def test_analyze_returns_cached_result(self):
        """Test analyze() returns cached result without fetching."""
        mock_fetcher = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            
            # Manually save a cached result
            analyzer._save_to_cache(0.6, 20)
            
            # Call analyze - should return cached without calling fetcher
            result = await analyzer.analyze()
            
            assert result is not None
            assert result.score == 0.6
            assert result.article_count == 20
            # Verify fetch_gold_news was NOT called
            mock_fetcher.fetch_gold_news.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_mixed_scores_and_textblob(self):
        """Test analyze() handles mix of pre-computed and TextBlob scores."""
        mock_fetcher = AsyncMock()
        
        news_items = [
            NewsItem(
                title="Gold rises",
                summary="Gold climbs",
                published=datetime.now(timezone.utc),
                source="Reuters",
                sentiment_score=0.8,
                relevance_score=1.0,
                url="https://example.com/1"
            ),
            NewsItem(
                title="Gold tumbles",
                summary="Gold prices fall",
                published=datetime.now(timezone.utc),
                source="Bloomberg",
                sentiment_score=None,  # Use TextBlob
                relevance_score=1.0,
                url="https://example.com/2"
            ),
        ]
        
        mock_fetcher.fetch_gold_news.return_value = news_items
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            result = await analyzer.analyze()
            
            assert result is not None
            assert result.article_count == 2
            # Mixed scores should produce some average
            assert -1.0 <= result.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_score_clamping(self):
        """Test that sentiment scores are clamped to [-1, 1]."""
        mock_fetcher = AsyncMock()
        
        # Create items that might sum to > 1.0
        news_items = [
            NewsItem(
                title="Gold surges",
                summary="Gold prices increase",
                published=datetime.now(timezone.utc),
                source="Reuters",
                sentiment_score=1.0,
                relevance_score=1.0,
                url="https://example.com/1"
            ),
        ]
        
        mock_fetcher.fetch_gold_news.return_value = news_items
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            result = await analyzer.analyze()
            
            assert result is not None
            assert -1.0 <= result.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_caches_result(self):
        """Test that analyze() caches the computed result."""
        mock_fetcher = AsyncMock()
        
        news_items = [
            NewsItem(
                title="Gold rises",
                summary="Gold climbs",
                published=datetime.now(timezone.utc),
                source="Reuters",
                sentiment_score=0.5,
                relevance_score=0.9,
                url="https://example.com/1"
            ),
        ]
        
        mock_fetcher.fetch_gold_news.return_value = news_items
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "cache.db")
            analyzer = SentimentAnalyzer(mock_fetcher, cache_db=cache_path)
            
            # First call - fetches
            result1 = await analyzer.analyze()
            assert result1 is not None
            
            # Reset mock to verify cache is used
            mock_fetcher.fetch_gold_news.reset_mock()
            
            # Second call - should use cache
            result2 = await analyzer.analyze()
            assert result2 is not None
            assert result1.score == result2.score
            
            # Verify fetch was not called again
            mock_fetcher.fetch_gold_news.assert_not_called()


@pytest.mark.asyncio
async def test_sentiment_analyzer_import():
    """Test that SentimentAnalyzer can be imported from analysis module."""
    from gold_signal_bot.analysis import SentimentAnalyzer, SentimentResult
    
    assert SentimentAnalyzer is not None
    assert SentimentResult is not None


@pytest.mark.asyncio
async def test_news_fetcher_import():
    """Test that NewsFetcher and NewsItem can be imported from data module."""
    from gold_signal_bot.data import NewsFetcher, NewsItem
    
    assert NewsFetcher is not None
    assert NewsItem is not None
