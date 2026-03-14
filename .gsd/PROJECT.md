# Gold Signal Bot

## What This Is

A real-time XAU/USD trading signal bot that sends Telegram alerts for day trading and swing trading. Uses a "fusion" approach combining multiple analysis methods (technical indicators, price action, news sentiment, ML predictions) to generate high-confidence buy/sell signals with entry points, stop loss, take profit targets, and reasoning.

## Core Value

Deliver actionable gold trading signals with clear entry/exit levels and confidence scores — reducing the guesswork in trading decisions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Real-time XAU/USD price data from free source
- [ ] Technical indicator analysis (RSI, moving averages, MACD, etc.)
- [ ] Support/resistance and price action detection
- [ ] News sentiment analysis for gold-related events
- [ ] ML-based pattern recognition and prediction
- [ ] Fusion engine that weighs and combines all signal sources
- [ ] Confidence scoring system for signals
- [ ] Telegram bot integration for instant alerts
- [ ] Signal format: BUY/SELL, entry price, SL, TP, reasoning, confidence
- [ ] Support for 1H, 4H, and Daily timeframes
- [ ] Signal performance tracking
- [ ] Deployable on free hosting service

### Out of Scope

- Auto-execution of trades — signals only, user decides
- Paid data sources — must work with free APIs
- Paid hosting — must deploy on free tier services
- Multiple currency pairs — XAU/USD only for v1

## Context

**Trading style:** Day trading and swing trading, meaning signals should be relevant for holding positions from hours to days/weeks.

**Timeframes:** 1H (day trading), 4H and Daily (swing trading).

**Signal approach:** "Fusion" methodology — no single indicator makes a signal. Multiple analysis methods must align, weighted by historical reliability.

**Delivery:** Telegram is primary and only alert channel.

## Constraints

- **Data**: Must use free real-time XAU/USD price feeds
- **Hosting**: Must run on free-tier cloud services (e.g., Railway, Render, Vercel, etc.)
- **Latency**: Alerts should arrive within reasonable time of signal generation (not millisecond-critical for day/swing trading)

## Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| Telegram for alerts | User preference, simple to implement | — Pending |
| Free data + free hosting | Budget constraint | — Pending |
| Fusion multi-indicator approach | More robust than single-indicator | — Pending |

---

_Last updated: March 14, 2026 after project initialization_
