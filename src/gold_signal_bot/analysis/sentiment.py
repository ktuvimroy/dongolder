"""Sentiment analysis for gold-related news with caching and fallback.

This module provides the SentimentAnalyzer class that aggregates sentiment
from gold-related news articles using both pre-computed Alpha Vantage scores
and TextBlob fallback when scores are unavailable.
"""

import logging
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Optional

from textblob import TextBlob

from src.gold_signal_bot.analysis.models import SentimentResult
from src.gold_signal_bot.data.news_fetcher import NewsFetcher

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes gold sentiment from news articles with caching.
    
    Uses NewsFetcher to retrieve gold-related news, processes sentiment scores
    (preferring pre-computed Alpha Vantage scores, falling back to TextBlob),
    and caches results to avoid rate limit exhaustion.
    """
    
    CACHE_TTL_HOURS = 1  # Re-fetch news every hour
    
    def __init__(self, news_fetcher: NewsFetcher, cache_db: Optional[str] = None):
        """Initialize SentimentAnalyzer.
        
        Args:
            news_fetcher: NewsFetcher instance for fetching news.
            cache_db: Optional SQLite database path for caching. If None,
                     uses data/sentiment_cache.db. Use ":memory:" or temp paths for testing.
        """
        self.news_fetcher = news_fetcher
        
        if cache_db is None:
            self.cache_db = "data/sentiment_cache.db"
        else:
            self.cache_db = cache_db
        
        self._init_cache_db()
    
    def _init_cache_db(self) -> None:
        """Initialize SQLite cache database.
        
        Creates sentiment_cache table if it doesn't exist.
        """
        try:
            # For in-memory databases, use URI to allow sharing across connections
            if self.cache_db == ":memory:":
                conn = sqlite3.connect("file::memory:?cache=shared", uri=True, check_same_thread=False)
            else:
                conn = sqlite3.connect(self.cache_db)
            
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_cache (
                    timestamp REAL PRIMARY KEY,
                    cached_at REAL NOT NULL,
                    score REAL NOT NULL,
                    article_count INTEGER NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize sentiment cache: {e}")
    
    def _get_cached_result(self) -> Optional[SentimentResult]:
        """Retrieve cached sentiment result if it exists and is fresh.
        
        Returns:
            SentimentResult if cached and within TTL, None otherwise.
        """
        try:
            # For in-memory databases, use URI to allow sharing across connections
            if self.cache_db == ":memory:":
                conn = sqlite3.connect("file::memory:?cache=shared", uri=True, check_same_thread=False)
            else:
                conn = sqlite3.connect(self.cache_db)
            
            cursor = conn.cursor()
            
            current_time = time.time()
            ttl_seconds = self.CACHE_TTL_HOURS * 3600
            
            cursor.execute(
                "SELECT score, article_count FROM sentiment_cache WHERE cached_at > ?",
                (current_time - ttl_seconds,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                score, article_count = result
                logger.debug(f"Using cached sentiment: {score} ({article_count} articles)")
                return SentimentResult.from_score(score, article_count)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to retrieve sentiment cache: {e}")
            return None
    
    def _save_to_cache(self, score: float, article_count: int) -> None:
        """Save sentiment result to cache.
        
        Args:
            score: Sentiment score to cache.
            article_count: Number of articles analyzed.
        """
        try:
            # For in-memory databases, use URI to allow sharing across connections
            if self.cache_db == ":memory:":
                conn = sqlite3.connect("file::memory:?cache=shared", uri=True, check_same_thread=False)
            else:
                conn = sqlite3.connect(self.cache_db)
            
            cursor = conn.cursor()
            
            current_time = time.time()
            
            # Clear old entries
            cursor.execute("DELETE FROM sentiment_cache")
            
            # Insert new entry
            cursor.execute(
                "INSERT INTO sentiment_cache (timestamp, cached_at, score, article_count) VALUES (?, ?, ?, ?)",
                (current_time, current_time, score, article_count)
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Cached sentiment: {score} ({article_count} articles)")
        
        except Exception as e:
            logger.error(f"Failed to save sentiment cache: {e}")
    
    def _analyze_text(self, text: str) -> float:
        """Fallback sentiment analysis using TextBlob.
        
        Args:
            text: Text to analyze (typically title + summary).
        
        Returns:
            Sentiment polarity score from -1.0 (negative) to 1.0 (positive).
        """
        try:
            blob = TextBlob(text)
            return float(blob.sentiment.polarity)
        except Exception as e:
            logger.debug(f"TextBlob analysis failed: {e}")
            return 0.0
    
    async def analyze(self) -> SentimentResult:
        """Analyze gold sentiment from recent news articles.
        
        Uses cached results if available (within TTL). Otherwise fetches
        news from Alpha Vantage NEWS_SENTIMENT API, computes average sentiment
        using pre-computed scores where available, TextBlob fallback for others.
        
        Returns:
            SentimentResult with aggregated sentiment score and signal direction.
        """
        # Check cache first
        cached = self._get_cached_result()
        if cached:
            return cached
        
        # Fetch fresh news
        try:
            news_items = await self.news_fetcher.fetch_gold_news(limit=50)
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            # Return neutral on error
            return SentimentResult.from_score(0.0, 0)
        
        if not news_items:
            logger.debug("No news items found")
            return SentimentResult.from_score(0.0, 0)
        
        # Compute weighted average sentiment
        total_score = 0.0
        weighted_count = 0.0
        
        for item in news_items:
            weight = item.relevance_score if item.relevance_score else 1.0
            
            # Use pre-computed score if available
            if item.sentiment_score is not None:
                sentiment = item.sentiment_score
            else:
                # Fallback to TextBlob analysis
                text = f"{item.title} {item.summary}".strip()
                sentiment = self._analyze_text(text)
            
            total_score += sentiment * weight
            weighted_count += weight
        
        # Calculate average sentiment
        avg_score = total_score / weighted_count if weighted_count > 0 else 0.0
        # Clamp to [-1, 1]
        avg_score = max(-1.0, min(1.0, avg_score))
        
        result = SentimentResult.from_score(avg_score, len(news_items))
        
        # Cache the result
        self._save_to_cache(avg_score, len(news_items))
        
        return result
