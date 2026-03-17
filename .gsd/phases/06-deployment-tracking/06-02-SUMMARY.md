---
phase: "06"
plan: "02"
subsystem: "signal-tracking"
tags: ["sqlite", "signal-history", "outcome-checker", "asyncio", "performance-tracking"]

dependency-graph:
  requires:
    - "06-01: db_path setting, gold_signals.db established"
    - "04-01/04-02: AlertManager and RawSignal structure"
    - "02-01: SpotPriceRepository for current price lookup"
  provides:
    - "SignalHistoryRepository: persists every sent signal to SQLite"
    - "OutcomeChecker: evaluates OPEN signals → WIN/LOSS/EXPIRED"
    - "AlertManager: now logs signals to DB after each successful send"
    - "main(): runs AlertManager and OutcomeChecker in parallel"
  affects:
    - "06-03: Telegram stats commands read from signal_history table"

tech-stack:
  added: []
  patterns:
    - "Repository pattern (same as SpotPriceRepository) for signal_history"
    - "asyncio.gather() for parallel periodic tasks in main loop"

key-files:
  created:
    - "src/gold_signal_bot/data/signal_history.py"
    - "src/gold_signal_bot/data/outcome_checker.py"
  modified:
    - "src/gold_signal_bot/telegram/alerts.py"
    - "src/gold_signal_bot/__init__.py"

decisions:
  - "INSERT OR IGNORE on signal_id for idempotent saves"
  - "reasoning stored as JSON string (no re-serialization on save)"
  - "OutcomeChecker reads spot_prices table for current price (same DB)"
  - "signal_history_repo=None default in AlertManager preserves backward compat"
  - "asyncio.gather() replaces bare await run_continuous() in main()"

metrics:
  duration: "~30 minutes"
  completed: "2026-03-17"
---

# Phase 06 Plan 02: Signal History & Outcome Tracking Summary

**One-liner:** SQLite signal_history table with WIN/LOSS/EXPIRED evaluation running as a parallel asyncio task alongside the alert loop.

## What Was Built

### SignalHistoryRepository (`signal_history.py`)

The data persistence layer for every signal the bot sends. Auto-creates `signal_history` table with `signal_id`, `sent_at`, `direction`, `timeframe`, `entry/stop/tp` prices, `confidence`, `reasoning` (JSON), and nullable outcome fields (`status`, `outcome_price`, `outcome_at`, `outcome_pnl_pct`).

Six public methods:
- `save_signal()` — INSERT OR IGNORE, idempotent on signal_id
- `get_open_signals()` — returns all status='OPEN', ordered oldest first
- `update_outcome()` — marks WIN/LOSS/EXPIRED with price and pnl_pct
- `get_recent(limit)` — last N signals across all statuses
- `get_stats()` — aggregate: wins, losses, win_rate_pct, avg/best/worst pnl
- `get_stats_by_timeframe()` — per-timeframe breakdown

### OutcomeChecker (`outcome_checker.py`)

Evaluates every OPEN signal against the current spot price:
- **BUY WIN**: current_price >= take_profit_1
- **BUY LOSS**: current_price <= stop_loss
- **SELL WIN**: current_price <= take_profit_1
- **SELL LOSS**: current_price >= stop_loss
- **EXPIRED**: hours_open >= max_hours_open (per-signal or global 48h default)

`check_open_signals()` is synchronous (no async needed for DB + math).
`run_periodic(interval_seconds)` is async, designed for `asyncio.create_task()`.

### Wiring in `alerts.py`

`AlertManager.__init__` accepts `signal_history_repo: SignalHistoryRepository | None = None`. After each successful Telegram send, `check_and_alert()` builds a `SignalRecord` and calls `save_signal()`. Wrapped in try/except so a DB error never prevents signal delivery.

### Wiring in `__init__.py`

`main()` now creates `SignalHistoryRepository`, `SpotPriceRepository`, and `OutcomeChecker`. The bare `await alert_manager.run_continuous()` is replaced with:

```python
await asyncio.gather(
    alert_manager.run_continuous(interval_seconds=settings.fetch_interval_seconds),
    outcome_checker.run_periodic(interval_seconds=settings.outcome_check_interval_seconds),
)
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| INSERT OR IGNORE on signal_id | Idempotent sends if bot retries |
| reasoning stored as pre-serialized JSON string | AlertManager serializes once; no double-encoding |
| OutcomeChecker reads spot_prices table | Same DB, zero extra API calls |
| signal_history_repo=None default | Backward-compatible with all existing tests |
| Both tasks in asyncio.gather() | Both run forever; one CancelledError cancels both cleanly |

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- All 111 existing tests pass without modification
- Task 1 inline verification: SignalHistoryRepository save/update/stats confirmed
- Task 2 inline verification: BUY WIN, BUY LOSS, EXPIRED, SELL WIN all correct

## Next Phase Readiness

- `get_stats()` and `get_stats_by_timeframe()` are ready for the Telegram `/stats` command in 06-03
- `get_recent(limit)` is ready for the `/history` command in 06-03
- No blockers for 06-03
