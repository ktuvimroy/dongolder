---
phase: 04-fusion-engine
plan: 02
subsystem: analysis
tags: [confidence, scoring, filtering, telegram, formatter]

dependency_graph:
  requires:
    - "04-01"  # FusionEngine provides weighted scoring
  provides:
    - "RawSignal with confidence field"
    - "Confidence-based signal filtering"
    - "Visual confidence display in Telegram"
  affects:
    - "05-*"  # Advanced analysis may use confidence scores

tech_stack:
  patterns:
    - "Confidence threshold filtering (MIN_CONFIDENCE = 0.50)"
    - "Conflict penalty calculation (5% per conflicting indicator)"
    - "Tiered confidence labels (HIGH/MEDIUM/LOW)"

key_files:
  modified:
    - "src/gold_signal_bot/analysis/models.py"
    - "src/gold_signal_bot/analysis/signals.py"
    - "src/gold_signal_bot/telegram/formatter.py"
    - "tests/test_formatter.py"

decisions:
  - "50% minimum confidence threshold to generate signals"
  - "5% penalty per conflicting indicator"
  - "Confidence tiers: HIGH (>=80%), MEDIUM (>=60%), LOW (<60%)"
  - "Visual bar using █/░ characters (10 segments)"

metrics:
  duration: "~15 minutes"
  completed: "2026-03-15"
---

# Phase 04 Plan 02: Confidence Scoring Integration Summary

**Confidence scoring integrated into signal generation with visual display in Telegram messages.**

## What Was Built

### 1. RawSignal Confidence Field
- Added `confidence: float` field (0.0-1.0) to RawSignal dataclass
- Added `confidence_percent` property returning 0-100 integer
- Added `confidence_tier` property returning HIGH/MEDIUM/LOW labels

### 2. FusionEngine Integration in SignalGenerator
- Replaced `MIN_SIGNAL_COUNT` with `MIN_CONFIDENCE = 0.50` (50% threshold)
- Added `CONFLICT_PENALTY = 0.05` (5% per conflicting indicator)
- Signals now use weighted fusion scores instead of simple indicator counts
- Confidence calculation: `base_confidence - (conflict_count * 0.05)`
- Signals below 50% confidence are filtered out
- Reasoning now includes confidence context and aligned indicators

### 3. Telegram Formatter Updates
- Added `EMOJI_CONFIDENCE = "📈"` constant
- Added `_confidence_bar()` helper generating visual bar (█░)
- Both HTML and plain text formatters display:
  - Confidence percentage with tier label
  - Visual 10-segment confidence bar
- Added 5 new tests for confidence display

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 50% minimum confidence | Filter low-quality signals while allowing reasonable trades |
| 5% conflict penalty | Penalize mixed indicator signals proportionally |
| Tier thresholds: 80%/60% | Intuitive HIGH/MEDIUM/LOW categorization |
| Visual bar format | Quick visual assessment of signal strength |

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `b610fa2` | Add confidence field to RawSignal model |
| 2 | `87a8f8a` | Integrate FusionEngine into SignalGenerator |
| 3 | `d1e3b5d` | Update formatter to display confidence |

## Verification Results

- ✅ `RawSignal.confidence` field exists with default 0.0
- ✅ `SignalGenerator.MIN_CONFIDENCE` returns 0.5
- ✅ All 22 formatter tests pass
- ✅ Signals include confidence percentage and tier
- ✅ Visual confidence bar displays correctly

## Example Output

```
🟢 GOLD BUY SIGNAL 🟢
1H timeframe

📍 Entry: $2650.00
🛑 Stop Loss: $2640.00
🎯 Take Profit 1: $2680.00
🎯 Take Profit 2: $2700.00

⚖️ Risk/Reward: 1:3.00
📈 Confidence: 75% (MEDIUM)
    ███████░░░

💡 Analysis:
• Confidence: 75% (MEDIUM)
• Indicators aligned: RSI, MACD, EMA
• RSI(14) oversold at 28.5
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 04 complete. All fusion engine infrastructure is now in place:
- Plan 04-01: Weighted multi-indicator fusion ✅
- Plan 04-02: Confidence scoring integration ✅

Ready to proceed to Phase 05: Advanced Analysis.
