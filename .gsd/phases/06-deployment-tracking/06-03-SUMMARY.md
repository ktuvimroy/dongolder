---
phase: 06-deployment-tracking
plan: 03
subsystem: telegram-commands
tags: [telegram, commands, stats, performance, history, deployment, checkpoint]

dependency-graph:
  requires:
    - 06-02: signal_history (provides SignalHistoryRepository for stats data)
    - 06-01: config/deployment (provides Settings with telegram credentials)
  provides:
    - /stats command: win rate, wins/losses/open count, avg P&L
    - /performance command: best/worst trade, per-timeframe breakdown
    - /history [N] command: last N signals with status icons
    - StatsCommandHandler as asyncio background task alongside AlertManager
  affects:
    - Phase 6 goal: "Win rate and performance metrics visible"

tech-stack:
  patterns:
    - python-telegram-bot ApplicationBuilder (polling) for command handling
    - Coexistence pattern: Bot (send-only) + Application (receive commands) on same token
    - Authorization guard: only responds to configured telegram_chat_id

key-files:
  created:
    - src/gold_signal_bot/telegram/commands.py
  modified:
    - src/gold_signal_bot/telegram/__init__.py
    - src/gold_signal_bot/__init__.py

decisions:
  - name: Separate Application instance for commands
    rationale: TelegramBot uses Bot directly for sending; StatsCommandHandler uses ApplicationBuilder for receiving — both can share the same token without conflict
  - name: Authorization guard in every command handler
    rationale: Only configured telegram_chat_id can trigger commands (security)
  - name: /history N supports 1-50 signals
    rationale: Capped at 50 to avoid Telegram message length limits

metrics:
  duration: ~10 minutes
  completed: 2026-03-17
  tasks: 2/3 (task 3 is deployment checkpoint — awaiting human verification)
  tests: 111 passed
---

# Phase 6 Plan 3: Telegram Stats Commands Summary

**One-liner:** /stats, /performance, /history Telegram commands backed by SignalHistoryRepository — running as background asyncio task alongside AlertManager.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create Telegram command handlers module | 379f5cd | telegram/commands.py |
| 2 | Wire StatsCommandHandler into main() and update telegram __init__ | 21dbe85 | telegram/__init__.py, __init__.py |

## What Was Built

### StatsCommandHandler (commands.py)

Three Telegram command handlers reading live data from `SignalHistoryRepository`:

- **`/stats`** — Quick summary: total, wins, losses, open count, win rate %, avg P&L
- **`/performance`** — Detailed: best/worst trade P&L, per-timeframe win rate breakdown
- **`/history [N]`** — Last N signals (default 10, max 50) with status icons: ✅ WIN ❌ LOSS ⏳ OPEN ⌛ EXPIRED

Security: all handlers check `_is_authorized()` — only `telegram_chat_id` can query.

### Main Wiring (__init__.py)

`main()` creates `StatsCommandHandler` and runs three coroutines in parallel:
```python
await asyncio.gather(
    alert_manager.run_continuous(...),
    outcome_checker.run_periodic(...),
    stats_handler.start_polling(),
)
```

### Telegram __init__.py

`StatsCommandHandler` added to `__all__` exports.

## Checkpoint: Deployment Verification (Task 3 — Blocking)

**Status:** ⏳ Awaiting human deployment

All code is implemented and committed. Task 3 requires choosing a hosting platform and verifying 24/7 operation.

### What's Needed

Choose **one** deployment path and complete setup:

**Path A — Oracle Cloud Always Free (zero cost forever):**
1. Provision Always Free Ampere A1 VM (Ubuntu 22.04, 2 OCPU, 4 GB RAM) at cloud.oracle.com
2. SSH in, install Python 3.11, clone repo, `pip install .`, `python -m textblob.download_corpora`
3. Create `.env` with all API keys + `DB_PATH=/home/ubuntu/data/gold_signals.db`
4. Copy `gold-signal-bot.service` to `/etc/systemd/system/`
5. `sudo systemctl enable --now gold-signal-bot`
6. Verify: `sudo systemctl status gold-signal-bot` → `active (running)`

**Path B — Railway Hobby (~$5/month, managed):**
1. Create Railway account, activate Hobby plan
2. New Project → Deploy from GitHub → select this repo
3. Add environment variables: `ALPHA_VANTAGE_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DB_PATH=/data/gold_signals.db`, `HEALTH_CHECK_PORT=8080`
4. Add Storage → Volume → mount path `/data`
5. Railway auto-detects Dockerfile → watch build log end with `AlertManager starting`

### Verification Checklist

- [ ] Bot is live on chosen host
- [ ] Logs show `AlertManager starting` and `Command handler: /stats /performance /history enabled`
- [ ] Send `/stats` to bot → replies (even if "No signals tracked yet.")
- [ ] Send `/performance` → replies with formatted report
- [ ] Send `/history` → replies with history (or empty message)
- [ ] After 2 hours: host shows bot still running (no crash loops)
- [ ] After first signal: `/stats` shows non-zero count

## Deviations from Plan

None — implementation matches plan specification exactly. `_is_authorized()` security guard was added (also in plan) and implemented correctly.
