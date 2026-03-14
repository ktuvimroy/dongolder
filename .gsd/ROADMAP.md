# Roadmap: Gold Signal Bot

## Overview

Build a fusion-based XAU/USD trading signal bot from the ground up. Start with reliable price data, add technical analysis, get signals flowing to Telegram (MVP), then enhance with advanced analysis methods and deploy to free hosting for 24/7 operation.

## Phases

- [ ] **Phase 1: Data Foundation** — Free XAU/USD price feed and data pipeline
- [ ] **Phase 2: Technical Analysis Engine** — Core indicators and basic signals
- [ ] **Phase 3: Telegram Signal Bot** — Alert delivery system (MVP complete)
- [ ] **Phase 4: Fusion Engine** — Multi-source signal combining and confidence scoring
- [ ] **Phase 5: Advanced Analysis** — News sentiment and ML pattern recognition
- [ ] **Phase 6: Deployment & Tracking** — Free hosting and performance monitoring

## Phase Details

### Phase 1: Data Foundation

**Goal**: Reliable real-time XAU/USD price data flowing through a clean pipeline
**Depends on**: Nothing (first phase)
**Requirements**: Real-time XAU/USD price data from free source, Support for 1H/4H/Daily timeframes
**Success Criteria** (what must be TRUE):
1. XAU/USD prices update in real-time from free API
2. Historical data available for 1H, 4H, and Daily timeframes
3. Data pipeline handles API failures gracefully
**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project setup and Alpha Vantage data fetcher with rate limiting
- [ ] 01-02-PLAN.md — Multi-timeframe data pipeline with SQLite storage and candle aggregation

### Phase 2: Technical Analysis Engine

**Goal**: Generate signals from technical indicators and price action
**Depends on**: Phase 1
**Requirements**: Technical indicator analysis, Support/resistance and price action detection
**Success Criteria** (what must be TRUE):
1. RSI, MACD, Moving Averages, Bollinger Bands calculated correctly
2. Support and resistance levels detected automatically
3. Raw technical signals generated (not yet fused)
**Plans**: TBD

Plans:
- [ ] 02-01: Core technical indicators
- [ ] 02-02: Support/resistance and price action detection

### Phase 3: Telegram Signal Bot

**Goal**: Deliver formatted trading signals to Telegram (MVP milestone)
**Depends on**: Phase 2
**Requirements**: Telegram bot integration, Signal format with entry/SL/TP/reasoning/confidence
**Success Criteria** (what must be TRUE):
1. Telegram bot sends messages when signals trigger
2. Signals include BUY/SELL, entry price, SL, TP levels
3. Signals include reasoning (which indicators triggered)
4. User receives alerts in real-time
**Plans**: TBD

Plans:
- [ ] 03-01: Telegram bot setup and signal formatting
- [ ] 03-02: Alert system integration

### Phase 4: Fusion Engine

**Goal**: Combine multiple analysis methods into weighted, high-quality signals
**Depends on**: Phase 3
**Requirements**: Fusion engine combining all signal sources, Confidence scoring system
**Success Criteria** (what must be TRUE):
1. Multiple indicators weighted and combined for each signal
2. Confidence score (0-100%) included with every signal
3. Signal quality improved vs. single-indicator approach
**Plans**: TBD

Plans:
- [ ] 04-01: Multi-indicator fusion logic
- [ ] 04-02: Confidence scoring system

### Phase 5: Advanced Analysis

**Goal**: Add news sentiment and ML-based pattern recognition
**Depends on**: Phase 4
**Requirements**: News sentiment analysis, ML-based pattern recognition
**Success Criteria** (what must be TRUE):
1. Gold-related news sentiment factored into signals
2. ML model identifies historical patterns
3. Advanced analysis improves signal accuracy
**Plans**: TBD

Plans:
- [ ] 05-01: News sentiment integration
- [ ] 05-02: ML pattern recognition

### Phase 6: Deployment & Tracking

**Goal**: Deploy to free hosting with performance tracking
**Depends on**: Phase 5
**Requirements**: Deployable on free hosting, Signal performance tracking
**Success Criteria** (what must be TRUE):
1. Bot runs 24/7 on free hosting service
2. Signal history logged with outcomes
3. Win rate and performance metrics visible
**Plans**: TBD

Plans:
- [ ] 06-01: Free hosting deployment
- [ ] 06-02: Performance tracking system

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/2 | Not started | - |
| 2. Technical Analysis Engine | 0/2 | Not started | - |
| 3. Telegram Signal Bot | 0/2 | Not started | - |
| 4. Fusion Engine | 0/2 | Not started | - |
| 5. Advanced Analysis | 0/2 | Not started | - |
| 6. Deployment & Tracking | 0/2 | Not started | - |
