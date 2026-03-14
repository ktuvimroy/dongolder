# Feature Landscape

**Domain:** XAU/USD Trading Signal Bot
**Researched:** March 14, 2026

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Real-time price alerts | Core value proposition | Medium | Must handle API rate limits |
| Basic TA indicators (RSI, MACD, MA) | Standard for any trading tool | Low | pandas-ta covers all |
| Entry/SL/TP levels | Users need actionable signals | Medium | Requires ATR-based calculations |
| Telegram delivery | User's specified channel | Low | Well-documented library |
| Multi-timeframe (1H, 4H, Daily) | Project requirement | Medium | Store OHLC per timeframe |
| Buy/Sell signal direction | Fundamental signal component | Low | Simple logic |
| Signal timestamp | Know when signal was generated | Low | UTC recommended |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Fusion confidence scoring** | Differentiates from single-indicator bots | High | Core differentiator - weight multiple sources |
| **Reasoning explanation** | Users understand WHY a signal fired | Medium | Concatenate triggered conditions |
| **News sentiment integration** | Avoid trading against major news | Medium | Alpha Vantage NEWS_SENTIMENT API |
| **ML pattern recognition** | Learns from historical patterns | High | Phase 5 feature - needs training data |
| **Support/resistance detection** | Key price levels for S/R traders | Medium | Swing high/low algorithm |
| **Performance tracking** | Know if signals are profitable | Medium | Track signal outcomes |
| **Risk/reward ratio** | Help users assess trades | Low | Calculate from SL/TP |
| **Trailing stop suggestions** | Advanced exit strategy | Medium | ATR-based trailing logic |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Auto-execution** | Regulatory risk, liability, complexity | Signals only - user decides |
| **Guaranteed profit claims** | Dishonest, invitation for complaints | Show historical hit rate, no promises |
| **Real-time tick data** | Free APIs don't support, not needed for swing | 1min minimum, 15min is fine for 1H+ signals |
| **Multiple currency pairs v1** | Scope creep, XAU/USD focus | Start with one, expand later |
| **Paid data sources** | Project constraint | Work within free API limits |
| **Complex UI/Dashboard** | Telegram-only delivery requirement | Keep it simple: chat messages |
| **Backtesting engine** | Nice-to-have but out of scope v1 | Manual validation first |
| **Social trading/copy trading** | Legal complexity, different product | Pure signal bot |
| **Options/leveraged signals** | Different risk profile | Spot XAU/USD only |

## Feature Dependencies

```
Phase 1: Data Foundation
├── Price feed working
├── Historical data loading
└── OHLC storage

Phase 2: Technical Analysis
├── Depends on: Phase 1
├── RSI, MACD, MA calculated
├── Bollinger Bands
└── Support/Resistance detection

Phase 3: Telegram Bot (MVP)
├── Depends on: Phase 2
├── Bot receives commands
├── Signals formatted and sent
└── Basic entry/SL/TP

Phase 4: Fusion Engine
├── Depends on: Phase 2, 3
├── Multiple signal sources combined
├── Confidence scoring
└── Reasoning generation

Phase 5: Advanced Analysis
├── Depends on: Phase 4
├── News sentiment
├── ML pattern recognition
└── Requires historical training

Phase 6: Deployment & Tracking
├── Depends on: all above
├── Free hosting deployed
├── Performance tracking
└── Signal outcome logging
```

## MVP Recommendation

For MVP (Phase 3), prioritize:

1. **XAU/USD price feed working** - Foundation
2. **Basic TA signals (RSI, MACD, MA)** - Core functionality
3. **Telegram alert delivery** - User interaction
4. **Entry/SL/TP calculation** - Actionable signals
5. **Simple confidence (aligned indicators count)** - Differentiation tease

Defer to post-MVP:
- News sentiment: Adds API complexity, save for Phase 5
- ML predictions: Needs training data accumulated first
- Performance tracking: Nice-to-have, focus on signals first
- Multi-pair support: Out of scope per requirements

## Signal Format Specification

Expected signal message format:

```
🟢 BUY SIGNAL - XAU/USD

📊 Timeframe: 4H
💰 Entry: $2,045.50
🎯 TP1: $2,065.00 (+0.95%)
🎯 TP2: $2,085.00 (+1.93%)
🛑 SL: $2,030.00 (-0.76%)
📈 R:R: 1:2.5

🔍 Confidence: 78% (HIGH)

📋 Reasoning:
• RSI(14) oversold bounce: 32 → 38
• MACD bullish crossover
• Price at daily support level
• EMA 21 acting as support

⚠️ News: No major gold news in 4H

⏰ Generated: 2026-03-14 10:30 UTC
```

## Confidence Score Components

| Component | Weight | Source |
|-----------|--------|--------|
| RSI signal alignment | 20% | Oversold/overbought + reversal |
| MACD signal alignment | 20% | Crossover direction |
| Trend alignment (MA) | 15% | Price vs EMA 21/50 |
| Bollinger Band position | 10% | Band touch + squeeze |
| Support/Resistance proximity | 15% | Near key level |
| News sentiment | 10% | Positive/negative/neutral |
| ML prediction (if available) | 10% | Model confidence |

**Confidence thresholds:**
- HIGH: 70%+ (strong signal)
- MEDIUM: 50-69% (moderate signal)
- LOW: <50% (weak signal, consider skipping)

## User Commands (Telegram)

| Command | Description | MVP? |
|---------|-------------|------|
| `/start` | Welcome message, bot info | Yes |
| `/status` | Current XAU/USD price | Yes |
| `/signal` | Generate signal for current price | Yes |
| `/subscribe` | Enable automatic signals | Yes |
| `/unsubscribe` | Disable automatic signals | Yes |
| `/timeframe 4H` | Set preferred timeframe | Yes |
| `/performance` | Show signal history stats | Post-MVP |
| `/help` | Command list | Yes |

## Sources

- Telegram Bot API limits: https://core.telegram.org/bots/faq#broadcasting-to-users
- Trading signal best practices: Industry standards, trading forums
- Risk/reward calculations: Standard trading formulas
