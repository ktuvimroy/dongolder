"""Data fetching and processing modules."""

from .aggregator import CandleAggregator
from .fetcher import (
    AlphaVantageError,
    DataFetcher,
    InvalidRequestError,
    RateLimitError,
)
from .models import OHLC, SpotPrice, Timeframe
from .news_fetcher import NewsFetcher, NewsItem, RateLimitExceededError
from .repository import OHLCRepository, SpotPriceRepository
from .scheduler import DataScheduler

__all__ = [
    # Fetcher
    "AlphaVantageError",
    "DataFetcher",
    "InvalidRequestError",
    "RateLimitError",
    # News Fetcher
    "NewsFetcher",
    "NewsItem",
    "RateLimitExceededError",
    # Models
    "OHLC",
    "SpotPrice",
    "Timeframe",
    # Repositories
    "OHLCRepository",
    "SpotPriceRepository",
    # Aggregator
    "CandleAggregator",
    # Scheduler
    "DataScheduler",
]
