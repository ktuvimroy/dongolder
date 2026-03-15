"""Alpha Vantage news sentiment fetcher for gold-related news.

This module provides the NewsFetcher class for retrieving gold-related news
from Alpha Vantage NEWS_SENTIMENT API with filtering for relevance.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from src.gold_signal_bot.config import Settings, get_settings


logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A single news article with sentiment data.
    
    Attributes:
        title: Article headline.
        summary: Brief article summary.
        published: Publication timestamp.
        source: News source name.
        sentiment_score: Alpha Vantage pre-computed sentiment (-1 to 1), may be None.
        relevance_score: How relevant to gold (0 to 1), may be None.
        url: Link to full article.
    """
    title: str
    summary: str
    published: datetime
    source: str
    sentiment_score: float | None = None
    relevance_score: float | None = None
    url: str | None = None


class NewsFetcher:
    """Async fetcher for gold-related news from Alpha Vantage NEWS_SENTIMENT API.
    
    Uses the same rate limiting approach as DataFetcher to stay within
    Alpha Vantage free tier limits (5/min, 25/day).
    
    Example:
        async with NewsFetcher() as fetcher:
            news = await fetcher.fetch_gold_news(limit=50)
            for item in news:
                print(f"{item.title}: {item.sentiment_score}")
    """
    
    # Minimum relevance score for filtering news items
    MIN_RELEVANCE_SCORE = 0.5
    
    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize NewsFetcher.
        
        Args:
            settings: Optional Settings instance. Uses get_settings() if not provided.
        """
        self.settings = settings or get_settings()
        self._session: aiohttp.ClientSession | None = None
        
        # Rate limiting state (shared approach with DataFetcher)
        self._minute_calls: deque[float] = deque()
        self._day_calls: deque[float] = deque()
        self._day_start: float = self._get_day_start()
        self._rate_limit_lock = asyncio.Lock()
    
    @staticmethod
    def _get_day_start() -> float:
        """Get timestamp for start of current UTC day."""
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start.timestamp()
    
    async def __aenter__(self) -> "NewsFetcher":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _enforce_rate_limits(self) -> None:
        """Wait if necessary to respect rate limits."""
        async with self._rate_limit_lock:
            now = time.time()
            
            # Check if day rolled over - reset daily counter
            current_day_start = self._get_day_start()
            if current_day_start > self._day_start:
                self._day_start = current_day_start
                self._day_calls.clear()
            
            # Remove calls older than 1 minute
            minute_ago = now - 60
            while self._minute_calls and self._minute_calls[0] < minute_ago:
                self._minute_calls.popleft()
            
            # Check per-minute limit
            if len(self._minute_calls) >= self.settings.rate_limit_per_minute:
                wait_time = 60 - (now - self._minute_calls[0])
                if wait_time > 0:
                    logger.info(f"Rate limit: waiting {wait_time:.1f}s for per-minute limit")
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    while self._minute_calls and self._minute_calls[0] < now - 60:
                        self._minute_calls.popleft()
            
            # Check per-day limit
            if len(self._day_calls) >= self.settings.rate_limit_per_day:
                logger.warning("Daily rate limit reached - returning empty results")
                raise RateLimitExceededError("Daily API limit reached")
            
            # Record this call
            self._minute_calls.append(now)
            self._day_calls.append(now)
    
    async def fetch_gold_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch gold-related news from Alpha Vantage NEWS_SENTIMENT API.
        
        Args:
            limit: Maximum number of news items to fetch (default 50).
        
        Returns:
            List of NewsItem objects filtered by relevance score >= 0.5.
            Returns empty list on API errors.
        """
        if not self.settings.alpha_vantage_api_key:
            logger.warning("No Alpha Vantage API key configured - returning empty news")
            return []
        
        try:
            await self._enforce_rate_limits()
        except RateLimitExceededError:
            return []
        
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        params = {
            "function": "NEWS_SENTIMENT",
            "topics": "financial_markets,economy_monetary",
            "tickers": "FOREX:XAU",
            "sort": "LATEST",
            "limit": str(limit),
            "apikey": self.settings.alpha_vantage_api_key,
        }
        
        try:
            async with self._session.get(
                self.settings.alpha_vantage_base_url, params=params
            ) as response:
                if response.status != 200:
                    logger.warning(f"News API returned status {response.status}")
                    return []
                
                data = await response.json()
                
                # Check for API error messages
                if "Error Message" in data or "Note" in data:
                    error_msg = data.get("Error Message") or data.get("Note")
                    logger.warning(f"News API error: {error_msg}")
                    return []
                
                return self._parse_feed(data.get("feed", []))
                
        except aiohttp.ClientError as e:
            logger.warning(f"News fetch failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching news: {e}")
            return []
    
    def _parse_feed(self, feed: list[dict[str, Any]]) -> list[NewsItem]:
        """Parse Alpha Vantage feed array into NewsItem objects.
        
        Args:
            feed: Raw feed array from API response.
        
        Returns:
            List of NewsItem objects with relevance_score >= MIN_RELEVANCE_SCORE.
        """
        items: list[NewsItem] = []
        
        for article in feed:
            try:
                # Extract gold-specific sentiment from ticker_sentiment
                sentiment_score = None
                relevance_score = None
                
                ticker_sentiments = article.get("ticker_sentiment", [])
                for ts in ticker_sentiments:
                    if ts.get("ticker") == "FOREX:XAU":
                        relevance_score = float(ts.get("relevance_score", 0))
                        sentiment_score = float(ts.get("ticker_sentiment_score", 0))
                        break
                
                # Use overall sentiment if no gold-specific found
                if sentiment_score is None:
                    overall_score = article.get("overall_sentiment_score")
                    if overall_score is not None:
                        sentiment_score = float(overall_score)
                
                # Filter by relevance
                if relevance_score is not None and relevance_score < self.MIN_RELEVANCE_SCORE:
                    continue
                
                # Parse publication time
                time_published = article.get("time_published", "")
                try:
                    # Format: 20240315T120000
                    published = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                    published = published.replace(tzinfo=timezone.utc)
                except ValueError:
                    published = datetime.now(timezone.utc)
                
                items.append(NewsItem(
                    title=article.get("title", ""),
                    summary=article.get("summary", ""),
                    published=published,
                    source=article.get("source", "Unknown"),
                    sentiment_score=sentiment_score,
                    relevance_score=relevance_score,
                    url=article.get("url"),
                ))
                
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping article due to parse error: {e}")
                continue
        
        return items


class RateLimitExceededError(Exception):
    """Raised when API rate limit is exceeded."""
    pass
