"""Alpha Vantage data fetcher with rate limiting and retry logic.

This module provides the DataFetcher class for retrieving XAU/USD gold prices
from Alpha Vantage API with proper rate limiting (5/min, 25/day for free tier)
and exponential backoff retry on transient failures.
"""

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import aiohttp

from src.gold_signal_bot.config import get_settings, Settings


class AlphaVantageError(Exception):
    """Base exception for Alpha Vantage API errors."""
    pass


class RateLimitError(AlphaVantageError):
    """Raised when Alpha Vantage rate limit is exceeded."""
    pass


class InvalidRequestError(AlphaVantageError):
    """Raised when the request to Alpha Vantage is invalid."""
    pass


class DataFetcher:
    """Async data fetcher for Alpha Vantage gold prices with rate limiting.
    
    Implements rate limiting using token bucket algorithm:
    - Tracks calls per minute (max 5 for free tier)
    - Tracks calls per day (max 25 for free tier)
    - Blocks/waits when limits exceeded
    
    Implements retry with exponential backoff:
    - Retries on 5xx errors and network errors
    - Max 3 retries with configurable initial backoff
    - Does NOT retry on 4xx (bad request)
    
    Example:
        async with DataFetcher() as fetcher:
            price = await fetcher.fetch_gold_spot()
            print(price)
    """
    
    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize DataFetcher.
        
        Args:
            settings: Optional Settings instance. Uses get_settings() if not provided.
        """
        self.settings = settings or get_settings()
        self._session: aiohttp.ClientSession | None = None
        
        # Rate limiting state
        self._minute_calls: deque[float] = deque()  # Timestamps of calls in last minute
        self._day_calls: deque[float] = deque()  # Timestamps of calls today
        self._day_start: float = self._get_day_start()
        
        # Lock for thread-safe rate limiting
        self._rate_limit_lock = asyncio.Lock()
    
    @staticmethod
    def _get_day_start() -> float:
        """Get timestamp for start of current UTC day."""
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start.timestamp()
    
    async def __aenter__(self) -> "DataFetcher":
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
        """Wait if necessary to respect rate limits.
        
        Implements token bucket algorithm for both per-minute and per-day limits.
        """
        async with self._rate_limit_lock:
            now = time.time()
            
            # Check if day rolled over - reset daily counter
            current_day_start = self._get_day_start()
            if current_day_start > self._day_start:
                self._day_calls.clear()
                self._day_start = current_day_start
            
            # Remove minute calls older than 60 seconds
            while self._minute_calls and now - self._minute_calls[0] > 60:
                self._minute_calls.popleft()
            
            # Remove day calls from previous days (shouldn't happen but safety check)
            while self._day_calls and self._day_calls[0] < self._day_start:
                self._day_calls.popleft()
            
            # Check per-minute limit
            if len(self._minute_calls) >= self.settings.rate_limit_per_minute:
                # Wait until oldest call is >60 seconds old
                wait_time = 60 - (now - self._minute_calls[0]) + 0.1
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Re-check after sleep
                    now = time.time()
                    while self._minute_calls and now - self._minute_calls[0] > 60:
                        self._minute_calls.popleft()
            
            # Check per-day limit
            if len(self._day_calls) >= self.settings.rate_limit_per_day:
                raise RateLimitError(
                    f"Daily rate limit of {self.settings.rate_limit_per_day} calls exceeded. "
                    f"Resets at midnight UTC."
                )
            
            # Record this call
            self._minute_calls.append(now)
            self._day_calls.append(now)
    
    async def _make_request(self, params: dict[str, str]) -> dict[str, Any]:
        """Make request to Alpha Vantage with rate limiting and retry logic.
        
        Args:
            params: Query parameters for the API request.
        
        Returns:
            JSON response from Alpha Vantage.
        
        Raises:
            RateLimitError: If rate limits are exceeded (either local or API-side).
            InvalidRequestError: If the request is invalid (4xx error).
            AlphaVantageError: For other API errors after retries exhausted.
        """
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        # Add API key to params
        params = {**params, "apikey": self.settings.alpha_vantage_api_key}
        
        # Enforce rate limits before making request
        await self._enforce_rate_limits()
        
        last_error: Exception | None = None
        backoff = self.settings.retry_backoff_seconds
        
        for attempt in range(self.settings.max_retries + 1):
            try:
                async with self._session.get(
                    self.settings.alpha_vantage_base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    # Don't retry 4xx errors
                    if 400 <= response.status < 500:
                        text = await response.text()
                        raise InvalidRequestError(
                            f"Invalid request (HTTP {response.status}): {text}"
                        )
                    
                    # Retry on 5xx errors
                    if response.status >= 500:
                        raise AlphaVantageError(
                            f"Server error (HTTP {response.status})"
                        )
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Check for Alpha Vantage error messages in response body
                    if "Error Message" in data:
                        raise InvalidRequestError(data["Error Message"])
                    
                    if "Note" in data and "call frequency" in data["Note"].lower():
                        raise RateLimitError(data["Note"])
                    
                    return data
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.settings.max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    
            except (InvalidRequestError, RateLimitError):
                # Don't retry these
                raise
                
            except AlphaVantageError as e:
                last_error = e
                if attempt < self.settings.max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
        
        raise AlphaVantageError(
            f"Request failed after {self.settings.max_retries + 1} attempts: {last_error}"
        )
    
    async def fetch_gold_spot(self) -> dict[str, Any]:
        """Fetch current XAU/USD spot price.
        
        Uses the CURRENCY_EXCHANGE_RATE function to get real-time gold price.
        
        Returns:
            Dict containing exchange rate data with keys:
            - Realtime Currency Exchange Rate (dict):
                - 1. From_Currency Code (XAU)
                - 2. From_Currency Name (Gold Ounce)
                - 3. To_Currency Code (USD)
                - 4. To_Currency Name (United States Dollar)
                - 5. Exchange Rate
                - 6. Last Refreshed
                - 7. Time Zone
                - 8. Bid Price
                - 9. Ask Price
        
        Raises:
            RateLimitError: If rate limits exceeded.
            InvalidRequestError: If request is malformed.
            AlphaVantageError: For other errors.
        """
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": "XAU",
            "to_currency": "USD",
        }
        return await self._make_request(params)
    
    async def fetch_gold_history(
        self,
        interval: str = "daily",
        outputsize: str = "compact",
    ) -> dict[str, Any]:
        """Fetch historical XAU/USD price data.
        
        Uses the FX_DAILY/FX_WEEKLY/FX_MONTHLY functions for historical data.
        
        Args:
            interval: Data interval - one of "daily", "weekly", "monthly".
            outputsize: "compact" (last 100 data points) or "full" (20+ years).
        
        Returns:
            Dict containing time series data with metadata and OHLC prices.
        
        Raises:
            ValueError: If interval is not valid.
            RateLimitError: If rate limits exceeded.
            InvalidRequestError: If request is malformed.
            AlphaVantageError: For other errors.
        """
        function_map = {
            "daily": "FX_DAILY",
            "weekly": "FX_WEEKLY",
            "monthly": "FX_MONTHLY",
        }
        
        if interval not in function_map:
            raise ValueError(
                f"Invalid interval '{interval}'. Must be one of: {list(function_map.keys())}"
            )
        
        params = {
            "function": function_map[interval],
            "from_symbol": "XAU",
            "to_symbol": "USD",
            "outputsize": outputsize,
        }
        return await self._make_request(params)
    
    @property
    def calls_remaining_minute(self) -> int:
        """Number of API calls remaining in current minute."""
        now = time.time()
        # Count calls in last 60 seconds
        recent_calls = sum(1 for t in self._minute_calls if now - t <= 60)
        return max(0, self.settings.rate_limit_per_minute - recent_calls)
    
    @property
    def calls_remaining_day(self) -> int:
        """Number of API calls remaining today."""
        current_day_start = self._get_day_start()
        if current_day_start > self._day_start:
            return self.settings.rate_limit_per_day
        return max(0, self.settings.rate_limit_per_day - len(self._day_calls))
