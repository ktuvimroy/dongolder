# Research Summary: Gold Signal Bot

**Domain:** XAU/USD Real-time Trading Signal Bot
**Researched:** March 14, 2026
**Overall confidence:** HIGH

## Executive Summary

Building a fusion-based XAU/USD signal bot on free infrastructure is **technically feasible** with careful API budget management. The core constraint is Alpha Vantage's free tier (25 requests/day, 5/minute), which is sufficient for 15-minute polling on 1H+ timeframes but requires disciplined rate limiting.

The recommended stack centers on **Python 3.11+ with python-telegram-bot 22.6** for async Telegram delivery, **pandas-ta** for technical indicators (150+ indicators, pure Python), and **SQLite** for local storage. Alpha Vantage provides the critical trifecta: live gold prices (GOLD_SILVER_SPOT), historical OHLC (GOLD_SILVER_HISTORY), and news sentiment (NEWS_SENTIMENT) - all in one free API.

The fusion approach differentiates this bot from simple single-indicator alerts. Combining RSI, MACD, moving averages, and sentiment into a weighted confidence score provides nuanced signals. ML pattern recognition (Phase 5) adds predictive capability once sufficient historical data accumulates.

**Primary risk:** Free hosting (Render) cold starts after 15min idle, potentially missing signals. Mitigation: self-ping keep-alive or upgrade to Fly.io paid (~$2/mo).

## Key Findings

**Stack:** Python 3.11+, Alpha Vantage (free), python-telegram-bot 22.6, pandas-ta 0.4.71b0, LightGBM 4.6+, SQLite, Render free tier

**Architecture:** Async data pipeline → Strategy-pattern analyzers → Weighted fusion engine → Telegram delivery. Single SQLite database, ~500 bar rolling window per timeframe.

**Critical pitfall:** ML overfitting and look-ahead bias are the biggest risks. Use walk-forward validation, only calculate indicators on closed candles, and start with simple models.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Data Foundation** - Establish reliable XAU/USD data pipeline
   - Addresses: Price feed, OHLC storage, rate limit management
   - Avoids: Rate limit exhaustion pitfall
   - LOW research risk: Alpha Vantage API is well-documented

2. **Technical Analysis** - Implement core indicators
   - Addresses: RSI, MACD, MA, Bollinger Bands, Support/Resistance
   - Avoids: Look-ahead bias pitfall
   - LOW research risk: pandas-ta handles standard indicators

3. **Telegram MVP** - Working bot with basic signals
   - Addresses: Command handling, signal formatting, delivery
   - Avoids: Telegram rate limit pitfall
   - LOW research risk: python-telegram-bot is mature

4. **Fusion Engine** - Weighted signal combination
   - Addresses: Multi-indicator fusion, confidence scoring, reasoning
   - Core differentiator implementation
   - MEDIUM research risk: Weight tuning needs experimentation

5. **Advanced Analysis** - Sentiment and ML integration
   - Addresses: News sentiment filter, ML pattern recognition
   - Avoids: Overfitting pitfall, sentiment misinterpretation pitfall
   - HIGH research risk: ML requires careful validation methodology

6. **Deployment & Tracking** - Production readiness
   - Addresses: Free hosting, performance tracking, signal logging
   - Avoids: Cold start pitfall
   - LOW research risk: Render deployment is straightforward

**Phase ordering rationale:**
- Phases 1-3 establish working MVP quickly (can deliver value within Phase 3)
- Phase 4 implements core differentiator (fusion)
- Phase 5 deferred because ML needs accumulated data from earlier phases
- Phase 6 last because deployment benefits from stable codebase

**Research flags for phases:**
- Phase 5: NEEDS deeper research (ML validation methodology, feature engineering)
- Phase 4: May need tuning research (fusion weights, confidence thresholds)
- Phases 1-3, 6: Standard patterns, unlikely to need additional research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified via PyPI and official docs |
| Features | HIGH | Standard trading bot features, well-understood domain |
| Architecture | HIGH | Patterns from python-telegram-bot wiki, standard async Python |
| Pitfalls | HIGH | Documented in trading algorithm literature and API docs |
| Data APIs | HIGH | Alpha Vantage endpoints tested, rate limits documented |
| Free Hosting | MEDIUM | Render cold start behavior documented but workarounds unverified |
| ML Integration | MEDIUM | Approach sound but walk-forward validation untested for this data |

## Gaps to Address

- **Intraday OHLC granularity:** Alpha Vantage free tier provides daily/weekly/monthly history only. For 1H/4H candles, may need to accumulate from live spot price over time, or accept delayed signals until sufficient data.
  
- **News sentiment relevance:** Alpha Vantage NEWS_SENTIMENT returns general gold news. Filtering for price-relevant news vs. mining company news requires experimentation.

- **Fusion weight tuning:** Initial weights proposed (20% RSI, 20% MACD, etc.) are educated guesses. May need adjustment based on backtest/live performance.

- **Cold start mitigation verification:** Self-ping keep-alive pattern documented but untested on Render. May need Fly.io paid if unreliable.

## API Summary

| API | Endpoint | Rate Limit | Use Case |
|-----|----------|------------|----------|
| Alpha Vantage | GOLD_SILVER_SPOT | 25/day, 5/min | Live gold price |
| Alpha Vantage | GOLD_SILVER_HISTORY | 25/day, 5/min | Daily+ OHLC history |
| Alpha Vantage | NEWS_SENTIMENT | 25/day, 5/min | Gold news sentiment |
| Telegram Bot API | sendMessage | 30/sec | Signal delivery |

**Budget allocation (25 calls/day):**
- Live price (GOLD_SILVER_SPOT): 20 calls (~every 72 min + buffer)
- News sentiment (NEWS_SENTIMENT): 4 calls (every 6 hours)
- History refresh (GOLD_SILVER_HISTORY): 1 call (daily)

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Alpha Vantage | Only free API with gold prices + sentiment |
| Telegram library | python-telegram-bot 22.6 | Best documented, async native |
| TA library | pandas-ta | Pure Python, 150+ indicators |
| ML library | LightGBM | Fast, scikit-learn compatible |
| Database | SQLite | Zero config, good enough for single user |
| Hosting | Render free | Free, sufficient for hobby |
| Python version | 3.11+ | Modern async, type hints |

## Files Created

| File | Purpose |
|------|---------|
| .gsd/research/SUMMARY.md | This file - executive summary |
| .gsd/research/STACK.md | Technology recommendations with versions |
| .gsd/research/FEATURES.md | Feature landscape (table stakes, differentiators) |
| .gsd/research/ARCHITECTURE.md | System structure and code patterns |
| .gsd/research/PITFALLS.md | Domain-specific mistakes to avoid |

## Ready for Roadmap

Research complete. All major domains investigated with HIGH confidence. Proceed to roadmap creation with:

- 6 phases as outlined above
- Phase 5 flagged for deeper research during discovery
- MVP achievable by end of Phase 3
- Full fusion capability by end of Phase 4

## Sources

Documented throughout research files. Primary sources:

- Alpha Vantage API: https://www.alphavantage.co/documentation/
- python-telegram-bot: https://python-telegram-bot.readthedocs.io/
- pandas-ta: https://github.com/twopirllc/pandas-ta
- LightGBM: https://lightgbm.readthedocs.io/
- Render: https://docs.render.com/
- Fly.io: https://fly.io/docs/about/pricing/
