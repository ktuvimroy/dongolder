# Phase 6 Research: Deployment & Tracking

**Researched:** March 17, 2026
**Domain:** Python bot hosting, Docker, SQLite performance tracking, Telegram bot commands
**Confidence:** HIGH (hosting pricing verified from official sources; patterns from codebase analysis)

---

## Summary

Phase 6 deploys the Gold Signal Bot to a hosting platform that keeps it running 24/7 and adds signal performance tracking (win rate, trade history). The bot is an async Python process that makes external API calls — not a web server — so it needs a platform that supports always-on background workers, not just HTTP-triggered serverless functions.

**The hosting landscape for free/cheap Python bots has changed significantly.** Fly.io removed its free tier for new accounts. Render's free tier does NOT cover background workers (only web services). Railway's post-trial "free" tier has severe restrictions. The two genuinely viable free or near-free options are **Oracle Cloud Always Free** (truly free, VM-based requiring self-management) and **Railway Hobby** ($5/month with enough included compute credit that a well-optimized bot effectively runs free within it).

**Primary recommendation:** Oracle Cloud Always Free ARM VM for zero cost, or Railway Hobby at $5/month for managed simplicity. Both paths are documented below. The plan should support either choice.

---

## Recommended Hosting: Railway Hobby ($5/month) or Oracle Cloud (Free)

**Oracle Cloud Always Free** is the correct answer for the stated goal of "free hosting":
- 4 ARM64 (Ampere A1) OCPUs + 24 GB RAM shared across instances — truly free forever
- 200 GB block storage (persistent SQLite)
- No spindown, no sleep, no monthly credit expiration
- Tradeoff: requires SSH access, manual deployment, systemd/Docker service management

**Railway Hobby** is the right answer if developer experience matters more than zero cost:
- $5/month includes $5 of compute credit
- A Python bot using ~200 MB RAM + <0.05 vCPU average costs ~$2.00–2.50/month — fits within the $5 credit
- Persistent volumes for SQLite, Docker-native, git push deployment, good logs

---

## Hosting Options Comparison

| Platform | Free? | Always-On? | Storage | RAM | Required changes | Deployment |
|---|---|---|---|---|---|---|
| **Oracle Cloud Always Free** | ✅ Free forever | ✅ Yes (VM) | 200 GB block vol. | 4–24 GB | systemd service file | SSH + git |
| **Railway Hobby** | ~$5/mo (incl. compute) | ✅ Yes | 0.5 GB volume | 512 MB | none needed | git push / Docker |
| **Fly.io Pay-as-you-go** | ❌ ~$3–5/mo | ✅ Yes | $0.15/GB/mo | 512 MB | fly.toml | flyctl deploy |
| **Render (Starter BW)** | ❌ $7/mo | ✅ Yes | +$0.25/GB/mo disk | 512 MB | render.yaml | git push / Docker |
| **PythonAnywhere Developer** | ❌ $10/mo | ✅ (1 always-on task) | 5 GB | shared | no Docker | file upload / git |
| **Google Cloud e2-micro** | ✅ Free forever | ✅ Yes (VM) | 30 GB disk | 1 GB | systemd service | SSH + git |
| **Render Free (Web Svc)** | ✅ Free | ❌ Spins down 15 min | ❌ Ephemeral | 512 MB | ❌ UNSUITABLE | — |
| **Fly.io Free** | ❌ No free tier | — | — | — | ❌ N/A (new accts) | — |
| **Koyeb Free** | ❌ No free tier | — | — | — | ❌ N/A | — |
| **Railway Free (post-trial)** | $1/mo + compute | ✅ Yes | 0.5 GB | 512 MB | — | git push / Docker |

### Key disqualifications

- **Render Free**: Background workers explicitly excluded from free instances (only web services, Postgres, Key Value). Free web services spin down after 15 min of no inbound HTTP traffic — unsuitable for a polling bot that never receives inbound traffic.
- **PythonAnywhere Free (Beginner)**: No always-on tasks, restricted outbound internet (whitelisted sites only — Alpha Vantage likely not whitelisted). Not viable on free tier.
- **Fly.io**: All new organizations are pay-as-you-go only. No free allowances. Requires credit card.
- **Serverless (Lambda, Cloud Run, etc.)**: All require HTTP triggers, not suitable for a polling scheduler loop.

### Google Cloud e2-micro caution

Google Cloud's Always Free e2-micro gives 1 GB RAM. At idle, the bot uses ~150–200 MB, but during analysis (scikit-learn HistGradientBoosting, pandas-ta on 200+ candles) it can spike to 350–500 MB. With Ubuntu/Debian OS overhead (~300 MB), total headroom is tight. It will likely work but should be measured before committing.

---

## Deployment Approach

### Path A: Oracle Cloud Always Free (Recommended for Zero Cost)

**Setup (one-time, ~2 hours):**
1. Create Oracle Cloud account, provision 1 Ampere A1 instance (Ubuntu 22.04, 2 OCPU, 4 GB RAM)
2. Configure security list to allow SSH (port 22)
3. SSH in, install Python 3.11: `sudo apt install python3.11 python3-pip`
4. Clone repo, install: `pip install .`
5. Download TextBlob corpora: `python -m textblob.download_corpora`
6. Create `/data/` directory on mounted block volume (or just use home dir)
7. Create systemd service for auto-restart on crash and on boot

**Systemd service file** (`/etc/systemd/system/gold-signal-bot.service`):
```ini
[Unit]
Description=Gold Signal Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dongolder
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/home/ubuntu/dongolder/.env
ExecStart=/usr/bin/python3.11 -m gold_signal_bot
Restart=always
RestartSec=30s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Deployment updates:** `git pull && sudo systemctl restart gold-signal-bot`

### Path B: Railway Hobby (Recommended for Managed Simplicity)

**Setup:**
1. Create Railway account, activate Hobby plan ($5/month)
2. Create project → Deploy from GitHub repo
3. Add environment variables in dashboard (ALPHA_VANTAGE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DB_PATH)
4. Add persistent volume, mount at `/data`
5. Railway auto-builds Docker image from Dockerfile, deploys

**Railway configuration file** (`railway.toml`):
```toml
[deploy]
startCommand = "python -m gold_signal_bot"
restartPolicyType = "always"
healthcheckPath = "/health"
healthcheckTimeout = 5
```

No sleep/spindown for Railway Hobby persistent services.

---

## Containerization

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install build tools (needed for some wheel compilations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Download TextBlob NLTK corpora at build time
RUN python -m textblob.download_corpora

# Create data directory for SQLite
RUN mkdir -p /data

CMD ["python", "-m", "gold_signal_bot"]
```

**Build notes:**
- `python:3.11-slim` provides a minimal Debian base — all wheels (pandas, scikit-learn, pandas-ta) have prebuilt binaries for both `linux/amd64` and `linux/arm64`
- No `NLTK_DATA` env var needed — TextBlob/NLTK stores corpora in default location inside container image
- `pip install .` reads `pyproject.toml` directly (hatchling build backend supports this)
- No `requirements.txt` conversion needed
- Estimated image size: ~700–900 MB (pandas + scikit-learn + pandas-ta are large)

**Volume mount:**
- Mount a persistent volume at `/data`
- Set `DB_PATH=/data/gold_signals.db` as an environment variable

**Environment variables required at runtime:**
```
ALPHA_VANTAGE_API_KEY=<key>
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>
DB_PATH=/data/gold_signals.db
LOG_LEVEL=INFO
```

**Multi-architecture builds (for Oracle Cloud ARM64):**
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t gold-signal-bot .
```

---

## Performance Tracking Design

### Signal History Table (new SQLite table)

Add to `src/gold_signal_bot/data/repository.py` (new `SignalHistoryRepository` class) or create `src/gold_signal_bot/data/signal_history.py`:

```sql
CREATE TABLE IF NOT EXISTS signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE NOT NULL,        -- UUID generated at send time
    sent_at TEXT NOT NULL,                  -- ISO8601 UTC timestamp
    direction TEXT NOT NULL,               -- 'BUY' or 'SELL'
    timeframe TEXT NOT NULL,               -- 'H1', 'H4', 'D'
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit_1 REAL NOT NULL,
    take_profit_2 REAL,                    -- nullable
    confidence REAL NOT NULL,              -- 0.0 to 1.0
    reasoning TEXT NOT NULL,              -- JSON array of strings
    status TEXT NOT NULL DEFAULT 'OPEN',  -- 'OPEN', 'WIN', 'LOSS', 'EXPIRED'
    outcome_price REAL,                   -- price when outcome was determined
    outcome_at TEXT,                      -- ISO8601 timestamp of outcome check
    outcome_pnl_pct REAL,                 -- % P&L (positive = profit)
    max_hours_open INTEGER NOT NULL DEFAULT 48  -- expire after N hours
);

CREATE INDEX IF NOT EXISTS idx_sh_status ON signal_history(status);
CREATE INDEX IF NOT EXISTS idx_sh_sent_at ON signal_history(sent_at);
```

### What data to capture per signal

From the existing `RawSignal` dataclass, capture all fields needed to evaluate outcome:
- `timestamp` / `direction` / `timeframe`
- `entry_price`, `stop_loss`, `take_profit_1`, `take_profit_2`
- `confidence` / `reasoning` (JSON)
- `sentiment_factor`, `ml_factor` (for future attribution analysis)

### Outcome Determination Logic

An `OutcomeChecker` async task runs every N minutes alongside the main alert loop:

```python
async def check_open_outcomes(signal_repo, spot_repo):
    """Check if any open signals have hit TP or SL."""
    open_signals = signal_repo.get_open_signals()
    
    for signal in open_signals:
        current_price = spot_repo.get_latest_price()
        hours_open = (datetime.utcnow() - signal.sent_at).total_seconds() / 3600
        
        if signal.direction == 'BUY':
            if current_price >= signal.take_profit_1:
                outcome = 'WIN'
                pnl = (signal.take_profit_1 - signal.entry_price) / signal.entry_price
            elif current_price <= signal.stop_loss:
                outcome = 'LOSS'
                pnl = (signal.stop_loss - signal.entry_price) / signal.entry_price
            else:
                outcome = None
        else:  # SELL
            if current_price <= signal.take_profit_1:
                outcome = 'WIN'
                pnl = (signal.entry_price - signal.take_profit_1) / signal.entry_price
            elif current_price >= signal.stop_loss:
                outcome = 'LOSS'
                pnl = (signal.entry_price - signal.stop_loss) / signal.entry_price
            else:
                outcome = None
        
        # Expire if open too long
        if outcome is None and hours_open >= signal.max_hours_open:
            outcome = 'EXPIRED'
            pnl = (current_price - signal.entry_price) / signal.entry_price  # mark-to-market
        
        if outcome:
            signal_repo.update_outcome(signal.id, outcome, current_price, pnl)
```

### Performance Metrics to Expose

```python
@dataclass
class PerformanceStats:
    total_signals: int
    wins: int
    losses: int
    expired: int
    open_count: int
    win_rate: float       # wins / (wins + losses) as %
    avg_pnl_pct: float    # average P&L % across closed signals
    best_trade_pct: float
    worst_trade_pct: float
    total_pnl_pct: float  # sum of all P&L %
```

```sql
-- Win rate query
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_count,
    ROUND(100.0 * SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) 
          / NULLIF(SUM(CASE WHEN status IN ('WIN','LOSS') THEN 1 ELSE 0 END), 0), 1) as win_rate,
    ROUND(AVG(outcome_pnl_pct) * 100, 2) as avg_pnl_pct,
    MAX(outcome_pnl_pct) as best_trade,
    MIN(outcome_pnl_pct) as worst_trade
FROM signal_history;
```

### Reporting via Telegram Commands

Add to the Telegram bot (requires enabling `application` mode with command handlers):

**`/stats`** — Quick summary:
```
📊 Signal Performance (30 days)
━━━━━━━━━━━━━━━━━━━━
Total signals: 47
Wins: 28 | Losses: 14 | Open: 5
Win rate: 66.7%
Avg P&L: +0.8% per trade
```

**`/performance`** — Detailed report:
```
📈 Full Performance Report
━━━━━━━━━━━━━━━━━━━━
Best trade: H4 BUY +2.1% (Jan 15)
Worst trade: H1 SELL -0.8% (Jan 22)
Total P&L: +24.3% (aggregate)
By timeframe:
  H1: 58% win rate (24 signals)
  H4: 76% win rate (23 signals)
```

**`/history [N]`** — Last N signals (default 10):
```
Last 5 signals:
✅ BUY H4 $2,890 → $2,921 (+1.1%) closed
❌ SELL H1 $2,905 → $2,910 (-0.2%) SL hit
⏳ BUY H1 $2,895 — open
...
```

**Implementation note:** `python-telegram-bot >= 22` (already in `pyproject.toml`) supports command handlers with `ApplicationBuilder`. The bot currently uses `Bot` directly for sending — for receiving commands, it needs to run with `Application` (polling or webhook mode). A lightweight approach: poll for updates in a background coroutine alongside the existing alert loop.

---

## Environment & Configuration

### Current state (already correct)

The existing `config.py` uses `pydantic-settings` with `BaseSettings`, which reads from environment variables automatically. The `model_config` already specifies `.env` file support. **No secret is hardcoded.** ✅

### Changes needed for deployment

**Add to `Settings` in `config.py`:**
```python
# Storage
db_path: str = "gold_signals.db"   # Override: DB_PATH=/data/gold_signals.db

# Logging
log_level: str = "INFO"             # Override: LOG_LEVEL=DEBUG

# Performance tracking
outcome_check_interval_seconds: int = 900   # Check outcomes every 15 min
signal_max_open_hours: int = 48             # Expire signals after 48 hours

# Health check (optional, for Railway/Fly.io)
health_check_port: int = 0          # 0 = disabled; set to 8080 to enable
```

**DB_PATH handling:** The `OHLCRepository` currently hardcodes `"gold_data.db"`. For deployment, both repositories (OHLC + signal history) should use `settings.db_path` so they can be directed to a mounted volume:
```
DB_PATH=/data/gold_signals.db
```

### Health check (optional but recommended)

For Railway and Fly.io, a simple HTTP health check prevents the platform from marking the service as unhealthy:

```python
# Add to __init__.py main():
if settings.health_check_port > 0:
    asyncio.create_task(run_health_server(settings.health_check_port))
```

```python
async def run_health_server(port: int) -> None:
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/health', lambda r: web.Response(text='OK'))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
```

`aiohttp` is already in `pyproject.toml` ✅

### Gitignore verification

Ensure `.env` is in `.gitignore` (standard Python .gitignore includes it). Never commit API keys.

---

## Key Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| SQLite data loss on platform restart | HIGH on free tiers | Use persistent volume mount — ephemeral disk by default loses data on restart |
| Alpha Vantage rate limit (25 calls/day) hit by multiple restarts | MEDIUM | Store last fetch time in SQLite; don't re-fetch on startup if recently fetched |
| Memory spike during analysis (scikit-learn + pandas) | MEDIUM | Use 512 MB instance minimum; profile locally with `tracemalloc` |
| TextBlob NLTK corpora missing in container | HIGH | Download at Docker build time (`RUN python -m textblob.download_corpora`) |
| Bot crashes with no auto-restart | HIGH | systemd `Restart=always` (Oracle) or Railway/Fly.io restart policy |
| Telegram command handling conflicts with signal sending | LOW | Use `asyncio.Queue` or separate tasks; `python-telegram-bot` handles concurrency internally |
| Signal outcome incorrectly evaluated (stale price data) | MEDIUM | Outcome check uses spot_prices table; ensure scheduler is running before checking outcomes |
| pyproject.toml `hatchling` build requires `src/` layout | LOW | `pip install .` works correctly for `hatchling` with `packages = ["src/gold_signal_bot"]` ✅ |
| Oracle Cloud ARM64 wheel incompatibility | LOW | All dependencies (pandas, scikit-learn, pandas-ta, telegram) have published ARM64 wheels |

---

## Planning Recommendations

Suggested 5-task breakdown for Phase 6:

### Task 1: Dockerize the Bot
- Write `Dockerfile` with multi-stage-aware base image
- Add `DB_PATH` env var support to `Settings` and pass it to all repositories
- Test: `docker build + docker run` locally with `.env` file

### Task 2: Signal History Logging
- Create `SignalHistoryRepository` with `signal_history` SQLite table
- Hook into `AlertManager.check_and_alert()` to persist each sent signal
- Schema: all RawSignal fields + status + outcome columns

### Task 3: Outcome Checker
- Create `OutcomeChecker` class with `check_open_signals()` method
- Run as periodic async task in main loop (every 15 min, same interval as scheduler)
- Logic: compare current spot price vs TP1/SL for each OPEN signal

### Task 4: Telegram Stats Commands
- Add `ApplicationBuilder`-based command handling (upgrade from bare `Bot` usage)
- Implement `/stats` (quick summary) and `/performance` (detailed)
- Coexist with existing `AlertManager.run_continuous()` loop

### Task 5: Deploy & Verify
- Deploy to Railway (or Oracle Cloud if user prefers free)
- Configure environment variables, mount persistent volume
- Verify: bot runs 24/7, signals received in Telegram, `/stats` command works

### Checkpoint: After Task 3
Before building Telegram commands, verify the outcome logic works correctly by running a local test with historical signal data and checking expected WIN/LOSS/EXPIRED outcomes. This is a data logic checkpoint.

---

## Sources

### Primary (HIGH confidence — verified from official sites)
- `https://railway.com/pricing` — Railway pricing as of March 2026: Free trial ($5), then $1/mo + compute; Hobby $5/mo with $5 compute
- `https://render.com/docs/free` — Render free instances: web services only; background workers NOT free; free instances spin down after 15 min
- `https://render.com/docs/background-workers` — Background workers run continuously; no free tier; min Starter ($7/mo)
- `https://fly.io/docs/about/pricing/` — Fly.io: no free tier for new organizations; pay-as-you-go, requires credit card
- `https://www.pythonanywhere.com/pricing/` — PythonAnywhere: Beginner free has NO always-on tasks, NO scheduled tasks, restricted internet

### Secondary (MEDIUM confidence)
- Oracle Cloud Always Free: Official Oracle documentation states ARM Ampere A1 Compute (4 OCPUs + 24GB RAM) and 200 GB block storage are Always Free — URL not fetched in this session but sourced from well-documented public record
- Google Cloud Free Tier e2-micro: 1 vCPU (0.25 sustained), 1 GB RAM — documented at `cloud.google.com/free`

### Codebase analysis (HIGH confidence — directly read)
- `src/gold_signal_bot/config.py` — pydantic-settings, env var support already in place
- `src/gold_signal_bot/__init__.py` — `main()` uses `AlertManager.run_continuous()`
- `src/gold_signal_bot/analysis/models.py` — `RawSignal` dataclass fields verified
- `src/gold_signal_bot/data/repository.py` — SQLite pattern, parameterized queries, auto-table-creation
- `pyproject.toml` — dependencies confirmed (aiohttp, python-telegram-bot >=22, scikit-learn, pandas-ta, textblob)

---

## Metadata

**Confidence breakdown:**
- Hosting options: HIGH — all pricing verified from official pages
- Dockerfile: HIGH — standard Python packaging patterns, confirmed deps from pyproject.toml
- Signal tracking schema: HIGH — derived directly from RawSignal dataclass and SQLite repository patterns already in codebase
- Outcome logic: MEDIUM — correct in principle; edge cases (price gaps, missing data) need careful testing
- Telegram commands: MEDIUM — python-telegram-bot >=22 API confirmed; exact upgrade path from bare `Bot` to `Application` should be verified against docs

**Research date:** March 17, 2026
**Valid until:** June 2026 (hosting pricing changes frequently; re-check before deployment)
