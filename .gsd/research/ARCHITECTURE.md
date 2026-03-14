# Architecture Patterns

**Domain:** XAU/USD Trading Signal Bot
**Researched:** March 14, 2026

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SIGNAL BOT SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  DATA LAYER  │───▶│ ANALYSIS     │───▶│  DELIVERY    │       │
│  │              │    │ LAYER        │    │  LAYER       │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                    │               │
│         ▼                   ▼                    ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Alpha       │    │  Fusion      │    │  Telegram    │       │
│  │  Vantage API │    │  Engine      │    │  Bot         │       │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤       │
│  │  - Gold Spot │    │  - TA Calc   │    │  - Signals   │       │
│  │  - History   │    │  - Sentiment │    │  - Commands  │       │
│  │  - News      │    │  - ML Model  │    │  - Status    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                                    │
│         └─────────▼─────────┘                                    │
│              ┌──────────────┐                                    │
│              │   STORAGE    │                                    │
│              │   (SQLite)   │                                    │
│              └──────────────┘                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **DataFetcher** | API calls to Alpha Vantage | Storage, Scheduler |
| **OHLCStorage** | SQLite database operations | DataFetcher, Analyzer |
| **TechnicalAnalyzer** | Calculate all TA indicators | OHLCStorage, FusionEngine |
| **SentimentAnalyzer** | Process news sentiment | DataFetcher, FusionEngine |
| **MLPredictor** | Make ML predictions | OHLCStorage, FusionEngine |
| **FusionEngine** | Combine signals, score confidence | All Analyzers, SignalFormatter |
| **SignalFormatter** | Format signals for Telegram | FusionEngine, TelegramBot |
| **TelegramBot** | Handle commands, send alerts | SignalFormatter, Scheduler |
| **Scheduler** | Orchestrate fetch/analyze cycles | All components |

### Data Flow

```
1. Scheduler triggers every N minutes
   │
   ▼
2. DataFetcher calls Alpha Vantage
   - GOLD_SILVER_SPOT for live price
   - GOLD_SILVER_HISTORY for OHLC (if needed)
   - NEWS_SENTIMENT for sentiment (if needed)
   │
   ▼
3. OHLCStorage persists data
   - Append new candles
   - Maintain rolling window (500 bars)
   │
   ▼
4. Analysis Layer processes
   │
   ├─▶ TechnicalAnalyzer: RSI, MACD, MA, BB, S/R
   ├─▶ SentimentAnalyzer: News score aggregation
   └─▶ MLPredictor: Pattern classification
   │
   ▼
5. FusionEngine combines
   - Weigh each signal source
   - Calculate confidence score
   - Generate reasoning text
   - Determine BUY/SELL/HOLD
   │
   ▼
6. If signal generated:
   │
   ▼
7. SignalFormatter creates message
   │
   ▼
8. TelegramBot sends to subscribers
```

## Patterns to Follow

### Pattern 1: Async Data Pipeline

**What:** Use asyncio for concurrent API calls and bot handling
**When:** All I/O operations (API calls, Telegram)
**Why:** Free tiers have rate limits; async maximizes throughput within limits

```python
import asyncio
import aiohttp

class DataFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self._session: aiohttp.ClientSession | None = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def fetch_gold_spot(self) -> dict:
        session = await self.get_session()
        params = {
            "function": "GOLD_SILVER_SPOT",
            "symbol": "XAU",
            "apikey": self.api_key
        }
        async with session.get(self.base_url, params=params) as resp:
            return await resp.json()
    
    async def fetch_gold_history(self, interval: str = "daily") -> dict:
        session = await self.get_session()
        params = {
            "function": "GOLD_SILVER_HISTORY",
            "symbol": "XAU",
            "interval": interval,  # daily, weekly, monthly
            "apikey": self.api_key
        }
        async with session.get(self.base_url, params=params) as resp:
            return await resp.json()
    
    async def close(self):
        if self._session:
            await self._session.close()
```

### Pattern 2: Repository Pattern for Storage

**What:** Abstract database operations behind a clean interface
**When:** All SQLite operations
**Why:** Testability, swappable storage backends

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import sqlite3

@dataclass
class OHLC:
    timestamp: datetime
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

class OHLCRepository(ABC):
    @abstractmethod
    async def save(self, candle: OHLC) -> None: ...
    
    @abstractmethod
    async def get_recent(self, timeframe: str, limit: int) -> list[OHLC]: ...

class SQLiteOHLCRepository(OHLCRepository):
    def __init__(self, db_path: str = "signals.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlc (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                UNIQUE(timestamp, timeframe)
            )
        """)
        conn.commit()
        conn.close()
    
    async def save(self, candle: OHLC) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO ohlc 
            (timestamp, timeframe, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            candle.timestamp.isoformat(),
            candle.timeframe,
            candle.open, candle.high, candle.low, candle.close,
            candle.volume
        ))
        conn.commit()
        conn.close()
    
    async def get_recent(self, timeframe: str, limit: int = 500) -> list[OHLC]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, timeframe, open, high, low, close, volume
            FROM ohlc WHERE timeframe = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (timeframe, limit))
        
        candles = [
            OHLC(
                timestamp=datetime.fromisoformat(row[0]),
                timeframe=row[1],
                open=row[2], high=row[3], low=row[4], close=row[5],
                volume=row[6]
            )
            for row in cursor.fetchall()
        ]
        conn.close()
        return list(reversed(candles))  # Chronological order
```

### Pattern 3: Strategy Pattern for Analyzers

**What:** Each indicator is a pluggable strategy
**When:** Adding new indicators without changing fusion logic
**Why:** Open/closed principle, testable units

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd
import pandas_ta as ta

@dataclass
class AnalysisResult:
    indicator: str
    signal: str  # "BUY", "SELL", "NEUTRAL"
    value: float
    reasoning: str
    confidence: float  # 0.0 to 1.0

class Analyzer(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> AnalysisResult: ...

class RSIAnalyzer(Analyzer):
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> AnalysisResult:
        df['rsi'] = ta.rsi(df['close'], length=self.period)
        rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        if rsi < self.oversold and rsi > prev_rsi:
            return AnalysisResult(
                indicator="RSI",
                signal="BUY",
                value=rsi,
                reasoning=f"RSI({self.period}) oversold bounce: {prev_rsi:.0f} → {rsi:.0f}",
                confidence=0.8
            )
        elif rsi > self.overbought and rsi < prev_rsi:
            return AnalysisResult(
                indicator="RSI",
                signal="SELL",
                value=rsi,
                reasoning=f"RSI({self.period}) overbought reversal: {prev_rsi:.0f} → {rsi:.0f}",
                confidence=0.8
            )
        else:
            return AnalysisResult(
                indicator="RSI",
                signal="NEUTRAL",
                value=rsi,
                reasoning=f"RSI({self.period}) neutral at {rsi:.0f}",
                confidence=0.5
            )

class MACDAnalyzer(Analyzer):
    def analyze(self, df: pd.DataFrame) -> AnalysisResult:
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        macd_line = df['MACD_12_26_9'].iloc[-1]
        signal_line = df['MACDs_12_26_9'].iloc[-1]
        prev_macd = df['MACD_12_26_9'].iloc[-2]
        prev_signal = df['MACDs_12_26_9'].iloc[-2]
        
        # Bullish crossover
        if prev_macd <= prev_signal and macd_line > signal_line:
            return AnalysisResult(
                indicator="MACD",
                signal="BUY",
                value=macd_line,
                reasoning="MACD bullish crossover",
                confidence=0.75
            )
        # Bearish crossover
        elif prev_macd >= prev_signal and macd_line < signal_line:
            return AnalysisResult(
                indicator="MACD",
                signal="SELL",
                value=macd_line,
                reasoning="MACD bearish crossover",
                confidence=0.75
            )
        else:
            return AnalysisResult(
                indicator="MACD",
                signal="NEUTRAL",
                value=macd_line,
                reasoning="MACD no crossover",
                confidence=0.5
            )
```

### Pattern 4: Fusion Engine with Weighted Voting

**What:** Combine multiple analysis results into single signal
**When:** Signal generation
**Why:** Core differentiator - weighted fusion vs single indicator

```python
@dataclass
class Signal:
    direction: str  # "BUY", "SELL", "HOLD"
    confidence: float
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    reasoning: list[str]
    timestamp: datetime

class FusionEngine:
    def __init__(self):
        self.analyzers: dict[str, tuple[Analyzer, float]] = {}
    
    def register(self, name: str, analyzer: Analyzer, weight: float):
        """Register analyzer with weight (weights should sum to 1.0)"""
        self.analyzers[name] = (analyzer, weight)
    
    def generate_signal(self, df: pd.DataFrame) -> Signal | None:
        results: list[AnalysisResult] = []
        weighted_score = 0.0
        
        for name, (analyzer, weight) in self.analyzers.items():
            result = analyzer.analyze(df)
            results.append(result)
            
            # Convert signal to score: BUY=+1, SELL=-1, NEUTRAL=0
            signal_score = {"BUY": 1, "SELL": -1, "NEUTRAL": 0}[result.signal]
            weighted_score += signal_score * weight * result.confidence
        
        # Determine direction from weighted score
        if weighted_score > 0.3:
            direction = "BUY"
        elif weighted_score < -0.3:
            direction = "SELL"
        else:
            return None  # No signal - HOLD
        
        # Calculate confidence (0-100%)
        confidence = min(abs(weighted_score) * 100, 100)
        
        # Calculate entry/SL/TP
        current_price = df['close'].iloc[-1]
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
        
        if direction == "BUY":
            entry = current_price
            stop_loss = current_price - (atr * 1.5)
            take_profit_1 = current_price + (atr * 2)
            take_profit_2 = current_price + (atr * 3)
        else:  # SELL
            entry = current_price
            stop_loss = current_price + (atr * 1.5)
            take_profit_1 = current_price - (atr * 2)
            take_profit_2 = current_price - (atr * 3)
        
        # Collect reasoning from aligned indicators
        reasoning = [r.reasoning for r in results if r.signal == direction]
        
        return Signal(
            direction=direction,
            confidence=confidence,
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            reasoning=reasoning,
            timestamp=datetime.utcnow()
        )
```

### Pattern 5: Scheduler with Rate Limit Awareness

**What:** Schedule jobs with API rate limit respect
**When:** Periodic data fetching and signal generation
**Why:** Free tier limits (5 req/min Alpha Vantage)

```python
from telegram.ext import Application, JobQueue
import asyncio

class SignalScheduler:
    def __init__(
        self,
        fetcher: DataFetcher,
        fusion_engine: FusionEngine,
        repository: OHLCRepository,
        bot_app: Application
    ):
        self.fetcher = fetcher
        self.fusion = fusion_engine
        self.repo = repository
        self.app = bot_app
        self.subscribers: set[int] = set()  # Chat IDs
    
    async def schedule_jobs(self):
        """Set up scheduled jobs - call after bot starts"""
        job_queue = self.app.job_queue
        
        # Fetch price every 15 minutes (4 req/hour, well under limit)
        job_queue.run_repeating(
            self.fetch_and_analyze,
            interval=900,  # 15 minutes
            first=10
        )
    
    async def fetch_and_analyze(self, context):
        try:
            # Fetch latest data
            data = await self.fetcher.fetch_gold_spot()
            # ... save to repo, build DataFrame ...
            
            # Generate signal
            df = await self._build_dataframe()
            signal = self.fusion.generate_signal(df)
            
            if signal and signal.confidence >= 50:
                await self._broadcast_signal(signal, context)
        
        except Exception as e:
            print(f"Error in fetch_and_analyze: {e}")
    
    async def _broadcast_signal(self, signal: Signal, context):
        message = SignalFormatter.format(signal)
        for chat_id in self.subscribers:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous API Calls

**What:** Using `requests` instead of `aiohttp` for API calls
**Why bad:** Blocks the event loop, Telegram bot becomes unresponsive
**Instead:** Always use async HTTP clients in async context

```python
# BAD - blocks event loop
import requests
def fetch_price():
    return requests.get(url).json()

# GOOD - non-blocking
import aiohttp
async def fetch_price():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
```

### Anti-Pattern 2: Hardcoded Thresholds

**What:** Magic numbers scattered through code
**Why bad:** Hard to tune, no single source of truth
**Instead:** Centralized configuration

```python
# BAD
if rsi < 30:  # magic number
    return "BUY"

# GOOD
@dataclass
class RSIConfig:
    period: int = 14
    oversold: int = 30
    overbought: int = 70

class RSIAnalyzer:
    def __init__(self, config: RSIConfig = RSIConfig()):
        self.config = config
```

### Anti-Pattern 3: Polling for Telegram Updates

**What:** Using getUpdates polling instead of webhooks or long polling
**Why bad:** Wastes CPU cycles, higher latency
**Instead:** python-telegram-bot's built-in polling or webhooks

```python
# BAD - manual polling loop
while True:
    updates = bot.get_updates()
    for update in updates:
        process(update)
    time.sleep(1)

# GOOD - use library's polling
application = Application.builder().token(TOKEN).build()
application.run_polling()
```

### Anti-Pattern 4: God Class Fusion

**What:** Single class that does data fetching, analysis, and delivery
**Why bad:** Untestable, violates SRP
**Instead:** Separate concerns per component diagram above

### Anti-Pattern 5: Recomputing Everything

**What:** Recalculating all indicators on every tick
**Why bad:** Wasted computation, slow
**Instead:** Incremental updates, cache recent calculations

## Scalability Considerations

| Concern | At 1 user | At 100 users | At 1000 users |
|---------|-----------|--------------|---------------|
| API calls | ~100/day fine | Same (shared data) | Same (shared data) |
| Telegram sends | Instant | Queue + rate limit | Batch + worker queue |
| Storage | SQLite fine | SQLite fine | Consider PostgreSQL |
| Hosting | Render free | Render free | Paid tier needed |
| Memory | 256MB fine | 256MB fine | May need 512MB |

For this project (personal use), 1 user scale is sufficient. Architecture supports growth.

## File Structure

```
gold_signal_bot/
├── main.py                 # Entry point, scheduler setup
├── config.py               # All configuration constants
├── requirements.txt        # Dependencies
├── signals.db              # SQLite database (gitignored)
│
├── data/
│   ├── __init__.py
│   ├── fetcher.py          # DataFetcher class
│   └── repository.py       # OHLCRepository, SQLite impl
│
├── analysis/
│   ├── __init__.py
│   ├── base.py             # Analyzer ABC, AnalysisResult
│   ├── technical.py        # RSI, MACD, MA, BB analyzers
│   ├── sentiment.py        # News sentiment analyzer
│   ├── ml_predictor.py     # ML model wrapper
│   └── fusion.py           # FusionEngine
│
├── delivery/
│   ├── __init__.py
│   ├── formatter.py        # SignalFormatter
│   └── telegram_bot.py     # Bot handlers, commands
│
└── tests/
    ├── __init__.py
    ├── test_analyzers.py
    ├── test_fusion.py
    └── test_repository.py
```

## Sources

- python-telegram-bot patterns: https://github.com/python-telegram-bot/python-telegram-bot/wiki
- pandas-ta documentation: https://github.com/twopirllc/pandas-ta
- asyncio best practices: Python official documentation
- Repository pattern: Martin Fowler's Patterns of Enterprise Application Architecture
