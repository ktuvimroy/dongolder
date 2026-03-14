# Technology Stack

**Project:** Gold Signal Bot (XAU/USD)
**Researched:** March 14, 2026

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Runtime | Native async support, mature ML ecosystem, excellent library availability |
| asyncio | stdlib | Async framework | Built-in, powers Telegram bot and concurrent data fetching |
| aiohttp | 3.9+ | HTTP client | Async HTTP for API calls, connection pooling |

### XAU/USD Price Data

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Alpha Vantage** | v1 API | **Primary - Historical & Daily** | Free tier: 25 req/day. `GOLD_SILVER_SPOT` for live, `GOLD_SILVER_HISTORY` for daily/weekly/monthly historical. Well-documented, reliable |
| **MetalpriceAPI** | v1 API | **Alternative - XAU rates** | Free tier: 100 req/month, daily delayed. Live rates, OHLC, historical. Supports hourly data (paid) |
| Yahoo Finance (yfinance) | 0.2+ | **Backup/Historical** | `GC=F` (Gold Futures) as proxy. Rate limited but free. Good for backtesting bulk data |

**Rate Limits Summary:**
- Alpha Vantage Free: 25 requests/day, 5/minute
- MetalpriceAPI Free: 100 requests/month, daily delay
- yfinance: Unofficial, ~2000 req/hour before throttling

### Technical Analysis

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **pandas-ta** | 0.4.71b0 | Primary TA library | 150+ indicators, pure Python, no C dependencies, DataFrame extension |
| pandas | 2.2+ | Data manipulation | Industry standard, excellent time series support |
| numpy | 1.26+ | Numerical computing | Required by pandas-ta, fast array operations |

**Indicators available in pandas-ta:**
- RSI: `ta.rsi(close, length=14)`
- MACD: `ta.macd(close, fast=12, slow=26, signal=9)`
- Bollinger Bands: `ta.bbands(close, length=20)`
- SMA/EMA: `ta.sma()`, `ta.ema()`
- ATR: `ta.atr()` for volatility
- Support/Resistance: Custom implementation using swing highs/lows

### Telegram Bot

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **python-telegram-bot** | 22.6 | Bot framework | Fully async, Telegram Bot API 9.3 support, excellent docs |
| aiolimiter | 1.2+ | Rate limiting | Optional: `pip install python-telegram-bot[rate-limiter]` |
| APScheduler | 3.11+ | Job scheduling | Optional: `pip install python-telegram-bot[job-queue]` for scheduled signals |

**Key Telegram limits:**
- 30 messages/second to same chat
- 1 message/second to same user in groups
- Message size: 4096 chars max

### News Sentiment

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Alpha Vantage NEWS_SENTIMENT** | v1 API | Gold news with sentiment | Free, returns sentiment scores for forex/commodities. Filter by `FOREX:XAU` |
| **NewsAPI** | v2 | General gold news | Free tier: 100 req/day, delayed 24h. Good for broader coverage |
| transformers (HuggingFace) | 4.40+ | Local sentiment | FinBERT model for financial sentiment if API limits hit |
| requests | 2.31+ | HTTP client | Sync calls for batch news processing |

**Alpha Vantage NEWS_SENTIMENT endpoint:**
```
https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=FOREX:XAU&apikey=YOUR_KEY
```
Returns: title, summary, sentiment_score (-1 to 1), relevance_score

### Machine Learning

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **scikit-learn** | 1.8+ | Classification/Regression | Random Forest, Gradient Boosting for signal classification |
| **LightGBM** | 4.6+ | Gradient boosting | Faster than sklearn, better for time series, scikit-learn compatible API |
| joblib | 1.4+ | Model persistence | Save/load trained models |

**Recommended ML approach:**
- **Classification:** Predict BUY/SELL/HOLD from feature vectors
- **Features:** TA indicators, sentiment scores, time features
- **Model:** LightGBM or Random Forest (not deep learning for v1)

**Why not LSTM/Deep Learning:**
- Requires more data (years of tick data)
- Harder to deploy on free tier (memory limits)
- Gradient boosting often outperforms for tabular data
- Simpler to interpret and debug

### Database/Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **SQLite** | stdlib | Local DB | Zero config, single file, perfect for free hosting |
| **SQLAlchemy** | 2.0+ | ORM | Optional: for cleaner DB access if needed |
| **JSON files** | - | Config/cache | Simple persistence for small data |

### Free Hosting

| Platform | Tier | Limitations | Best For |
|----------|------|-------------|----------|
| **Render** | Free | Spins down after 15min idle, 750 hours/month, ephemeral disk | Recommended: Good free tier, easy Python deploy |
| **Fly.io** | Pay-as-you-go | ~$1.94/mo for always-on shared VM, legacy free tier honored | Best uptime but not truly free |
| **Railway** | Usage-based | Trial credit, then pay-as-you-go | Not recommended: No free tier |
| **PythonAnywhere** | Free | 100s CPU/day, limited outbound, scheduled tasks | Backup option: scheduled-only signals |

**Render Free Tier Details:**
- 750 instance hours/month (enough for 1 always-running service with downtime)
- Spins down after 15min idle → 1min cold start on wake
- No persistent disk (ephemeral filesystem)
- Workaround: Store state in external DB or keep bot polling to stay warm

**Recommended Strategy:**
1. Use Render free tier for MVP
2. Accept 15-min idle spin-down (ping every 14 min via cron if needed)
3. Store critical state in SQLite file reloaded on startup
4. Migrate to Fly.io ($2/mo) if uptime becomes critical

## Installation

```bash
# Core
pip install python-telegram-bot[job-queue] pandas pandas-ta aiohttp requests

# ML
pip install scikit-learn lightgbm joblib

# Optional: Local sentiment
pip install transformers torch --index-url https://download.pytorch.org/whl/cpu
```

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
ALPHA_VANTAGE_API_KEY=your_av_key

# Optional
METALPRICEAPI_KEY=your_metal_key
NEWSAPI_KEY=your_news_key
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Price Data | Alpha Vantage | Polygon.io | Polygon requires paid plan for forex |
| Price Data | Alpha Vantage | Twelve Data | Free tier too limited (800/day but restrictive) |
| TA Library | pandas-ta | TA-Lib | TA-Lib requires C compilation, harder to deploy |
| Telegram | python-telegram-bot | Telethon | PTB is official, better for bots (Telethon is for user accounts) |
| ML | LightGBM | XGBoost | LightGBM faster, similar accuracy |
| ML | scikit-learn | TensorFlow | Overkill for v1, memory-heavy for free hosting |
| Hosting | Render | Heroku | Heroku removed free tier |
| Hosting | Render | Vercel | Vercel doesn't support long-running Python processes |

## API Endpoints Reference

### Alpha Vantage - Gold Spot Price
```
GET https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&symbol=XAU&apikey=KEY
```

### Alpha Vantage - Gold Historical (Daily/Weekly/Monthly)
```
GET https://www.alphavantage.co/query?function=GOLD_SILVER_HISTORY&symbol=XAU&interval=daily&apikey=KEY
```

### Alpha Vantage - News Sentiment
```
GET https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=FOREX:XAU&apikey=KEY&limit=50
```

### MetalpriceAPI - Live Rates
```
GET https://api.metalpriceapi.com/v1/latest?api_key=KEY&base=USD&currencies=XAU
```

### MetalpriceAPI - OHLC
```
GET https://api.metalpriceapi.com/v1/ohlc?api_key=KEY&base=XAU&currency=USD&date=2026-03-14
```

## Sources

- Alpha Vantage Documentation: https://www.alphavantage.co/documentation/
- MetalpriceAPI Documentation: https://metalpriceapi.com/documentation
- python-telegram-bot: https://python-telegram-bot.readthedocs.io/
- pandas-ta: https://www.pandas-ta.dev/
- Render Free Tier: https://render.com/docs/free
- Fly.io Pricing: https://fly.io/docs/about/pricing/
- LightGBM: https://lightgbm.readthedocs.io/
- scikit-learn: https://scikit-learn.org/
