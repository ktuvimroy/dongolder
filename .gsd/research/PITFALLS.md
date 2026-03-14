# Domain Pitfalls

**Domain:** XAU/USD Trading Signal Bot
**Researched:** March 14, 2026

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: ML Overfitting on Training Data

**What goes wrong:** Model performs perfectly on historical data, fails on live data
**Why it happens:**
- Training on too few samples
- Testing on data the model has seen
- Optimizing hyperparameters on test set
- Indicator parameters tuned to past performance

**Consequences:**
- False confidence in signal accuracy
- Real-money losses when deployed
- Complete model rebuild required

**Prevention:**
- Walk-forward validation: train on past, test on future only
- Minimum 1000+ samples for training
- Separate train/validation/test splits (60/20/20)
- Out-of-sample testing only
- Simple models first (Random Forest) before complex (deep learning)

**Detection:**
- Accuracy drops significantly on new data
- Model predictions cluster (always says BUY or SELL)
- Perfect backtest results (too good to be true)

### Pitfall 2: Look-Ahead Bias in Indicators

**What goes wrong:** Using future data to calculate current indicators
**Why it happens:**
- Using pandas operations that peek at future rows
- Centering moving averages instead of trailing
- Using close price of current incomplete candle
- Repainting indicators (update historical values)

**Consequences:**
- Backtest shows impossible performance
- Live trading fails completely
- All historical analysis invalid

**Prevention:**
- Only use `.shift(1)` for previous values, never forward
- Wait for candle close before calculating
- Use trailing (right-aligned) moving averages
- Test indicator values match real-time calculation

**Detection:**
- Signals fire "too late" in live trading
- Historical signals don't match what would have fired live

### Pitfall 3: API Rate Limit Exhaustion

**What goes wrong:** Free tier quota exceeded, data stops flowing
**Why it happens:**
- Too frequent polling (every second instead of every 15 min)
- No caching of responses
- Retry loops without backoff
- Multiple processes competing for same API key

**Consequences:**
- Bot goes blind (no price data)
- Signals stop generating
- May require waiting 24h for quota reset

**Prevention:**
```python
# Alpha Vantage free tier: 25 calls/day, 5/minute
# Budget: 4 calls/hour = 96/day, well under limit

FETCH_INTERVAL_SECONDS = 900  # 15 minutes
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60

# Cache responses
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=100)
def get_cached_price(timestamp_minute: str):
    # Cache key is minute, so same minute returns cached
    return fetch_price()
```

**Detection:**
- API returns 429 or rate limit error messages
- Alpha Vantage returns: `"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."`

### Pitfall 4: Free Hosting Cold Start Killing Signals

**What goes wrong:** Render free tier spins down after 15min, misses signals
**Why it happens:**
- No activity = container sleeps
- Cold start takes 30-60 seconds
- By the time it wakes, opportunity passed

**Consequences:**
- Missed trading signals
- Inconsistent signal timing
- User frustration

**Prevention:**
- Option 1: Accept limitation for hobby project
- Option 2: Self-ping every 10 minutes to stay warm
- Option 3: Switch to Fly.io paid (~$2/mo) for always-on
- Option 4: Use Telegram webhook (incoming message wakes bot)

```python
# Self-ping to stay warm (add to scheduler)
import aiohttp

async def keep_alive(context):
    """Ping self to prevent cold start"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://your-app.onrender.com/health"):
                pass
    except:
        pass  # Ignore errors, just need to trigger

# Add job
job_queue.run_repeating(keep_alive, interval=600)  # Every 10 min
```

**Detection:**
- Logs show gaps in scheduled job execution
- First signal after idle has old timestamp

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Telegram Rate Limits for Broadcasting

**What goes wrong:** Sending too many messages too fast gets bot temporarily banned
**Why it happens:**
- Telegram limits: ~30 messages/second to different chats
- Bulk notifications to many subscribers simultaneously

**Prevention:**
```python
import asyncio

async def broadcast_with_rate_limit(bot, chat_ids, message):
    """Send to all subscribers with rate limiting"""
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, message)
            await asyncio.sleep(0.05)  # 50ms between messages
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")
```

**Detection:**
- Telegram returns `RetryAfter` exception
- Some users don't receive messages

### Pitfall 6: Indicator Parameter Optimization Trap

**What goes wrong:** Spending weeks tuning RSI(14) vs RSI(12) vs RSI(16)
**Why it happens:**
- Belief that perfect parameters exist
- Optimizing for past performance (curve fitting)
- Diminishing returns not recognized

**Prevention:**
- Use industry standard parameters first (RSI 14, MACD 12/26/9)
- Only tune if significant underperformance
- Accept that parameters that worked before may not work again
- Time-box tuning: max 1 hour, then move on

**Detection:**
- Hyperparameter spreadsheets with 100+ combinations
- Different "optimal" parameters for each backtest period

### Pitfall 7: Sentiment Score Misinterpretation

**What goes wrong:** Treating sentiment as directional signal when it's not
**Why it happens:**
- News sentiment ≠ price direction
- "Gold prices fall" has negative sentiment but may be BUY opportunity
- Sentiment about gold mining ≠ sentiment about gold price

**Prevention:**
- Use sentiment as filter, not signal
- Negative news + technical BUY = reduce confidence, don't flip
- Focus on "relevance" score from API, filter low relevance
- Treat sentiment as tie-breaker, not primary indicator

**Detection:**
- Signals flip direction due to single news article
- Contradictory signals from sentiment vs technicals

### Pitfall 8: Missing Error Handling for External APIs

**What goes wrong:** Bot crashes on API error, stays dead
**Why it happens:**
- Happy path coding
- No try/catch around API calls
- No fallback when API unavailable

**Prevention:**
```python
async def safe_fetch_price(self) -> dict | None:
    """Fetch with error handling and fallback"""
    try:
        data = await self.fetcher.fetch_gold_spot()
        if "Note" in data:  # Rate limit message
            print(f"Rate limited: {data['Note']}")
            return None
        return data
    except aiohttp.ClientError as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching price: {e}")
        return None
```

**Detection:**
- Bot stops responding
- Logs show unhandled exceptions

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 9: Timezone Confusion

**What goes wrong:** Signals show wrong time, user confusion
**Why it happens:**
- Mixing local time and UTC
- API returns different timezone than expected
- Server timezone differs from user timezone

**Prevention:**
- Store all times as UTC internally
- Display with explicit timezone: "10:30 UTC"
- Use `datetime.utcnow()` not `datetime.now()`

### Pitfall 10: SQLite Concurrent Write Issues

**What goes wrong:** Database locked errors under load
**Why it happens:**
- SQLite has one writer at a time
- Async code may attempt concurrent writes

**Prevention:**
```python
# Use connection pooling or single connection with queue
import asyncio

class DBWriter:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._conn = None
    
    async def write(self, query, params):
        await self._queue.put((query, params))
    
    async def process_queue(self):
        """Single writer processes queue"""
        self._conn = sqlite3.connect("signals.db")
        while True:
            query, params = await self._queue.get()
            self._conn.execute(query, params)
            self._conn.commit()
```

### Pitfall 11: Floating Point Precision in Price Comparison

**What goes wrong:** Price comparisons fail due to float imprecision
**Why it happens:**
- `2045.50 == 2045.50` may be False due to float representation

**Prevention:**
```python
from decimal import Decimal

# For storage and comparison
price = Decimal(str(price_float))

# Or use tolerance
def prices_equal(a: float, b: float, tolerance: float = 0.01) -> bool:
    return abs(a - b) < tolerance
```

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Data Foundation | Rate limit exhaustion | Conservative polling, caching |
| Technical Analysis | Look-ahead bias | Only use closed candles |
| Telegram Bot | Rate limits on broadcast | Add delays between sends |
| Fusion Engine | Over-weighting correlated indicators | Diversify signal sources |
| ML Integration | Overfitting | Walk-forward validation |
| Deployment | Cold start signal gaps | Keep-alive pings or paid tier |

## Testing Checklist

Before going live, verify:

- [ ] No future data leakage in indicators
- [ ] Rate limits respected (test overnight)
- [ ] Error handling for all API calls
- [ ] Cold start recovery works
- [ ] Telegram messages deliver correctly
- [ ] Times display in expected timezone
- [ ] Database handles concurrent access
- [ ] Signal format matches specification

## Sources

- Alpha Vantage rate limit docs: https://www.alphavantage.co/support/
- Telegram bot limits: https://core.telegram.org/bots/faq#broadcasting-to-users
- ML trading pitfalls: Academic literature on algorithmic trading
- Render cold start: https://docs.render.com/free
- SQLite concurrency: https://sqlite.org/faq.html#q5
