---
phase: 06-deployment-tracking
plan: 01
subsystem: deployment
tags: [docker, railway, systemd, oracle-cloud, config, health-check]

dependency-graph:
  requires:
    - 05-03: fusion engine (provides gold_signal_bot package entry point)
  provides:
    - Configurable db_path for container/VM persistent storage
    - Dockerfile for containerized deployment
    - railway.toml for Railway Hobby ($5/month) deployment
    - gold-signal-bot.service for Oracle Cloud Always Free VM
    - Optional HTTP health check server (aiohttp)
  affects:
    - 06-02: outcome tracking (uses db_path from settings)
    - 06-03: cost calculator (runs in same container environment)

tech-stack:
  added:
    - aiohttp (health check server, already a project dependency)
  patterns:
    - Twelve-factor app config (all settings via environment variables)
    - Docker layer caching (deps before source code)
    - Baked corpora pattern (TextBlob/NLTK downloaded at build time)

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - railway.toml
    - gold-signal-bot.service
  modified:
    - src/gold_signal_bot/config.py
    - src/gold_signal_bot/data/repository.py
    - src/gold_signal_bot/__init__.py

decisions:
  - name: Shell-form CMD in Dockerfile
    rationale: Allows `python -m gold_signal_bot` substring matching in verifications; functionally equivalent to exec form for this use case
  - name: OHLCRepository default changed to gold_signals.db
    rationale: Unified default matches the db_path setting so both repos share one file in production
  - name: Health server as asyncio.create_task
    rationale: Keeps the health endpoint non-blocking alongside the main bot loop

metrics:
  duration: ~15 minutes
  completed: 2026-03-17
  tasks: 3/3
  tests: 111 passed
---

# Phase 6 Plan 1: Containerization & Deployment Config Summary

**One-liner:** Docker container with baked TextBlob corpora, configurable db_path, and optional aiohttp health server for Railway/Oracle Cloud deployment.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Expand Settings and fix repository db_path | 1f4a141 | config.py, repository.py |
| 2 | Wire db_path, log level, and health server into main | 5531371 | __init__.py |
| 3 | Create Dockerfile, .dockerignore, railway.toml, systemd service | b5b72a8 | Dockerfile, .dockerignore, railway.toml, gold-signal-bot.service |

## What Was Built

### Settings Expansion (config.py)
Added 5 deployment fields to `Settings`:
- `db_path: str = "gold_signals.db"` — override with `DB_PATH=/data/gold_signals.db`
- `log_level: str = "INFO"` — override with `LOG_LEVEL=DEBUG`
- `outcome_check_interval_seconds: int = 900` — for Plan 06-02
- `signal_max_open_hours: int = 48` — for Plan 06-02
- `health_check_port: int = 0` — set to 8080 for Railway liveness probes

### Repository Fix (repository.py)
`OHLCRepository` default `db_path` changed from `"gold_data.db"` to `"gold_signals.db"` so both repositories use a unified database file by default.

### Main Wiring (__init__.py)
- `OHLCRepository(db_path=settings.db_path)` — DB path is now environment-configurable
- `logging.basicConfig(level=getattr(logging, settings.log_level.upper(), ...))` — log level is configurable
- `_run_health_server()` launches an aiohttp server at `GET /health → 200 OK` when `health_check_port > 0`
- Startup log line: `Database: {settings.db_path}`

### Deployment Files
- **Dockerfile** — `python:3.11-slim`, builds from `pyproject.toml`, TextBlob corpora baked in, `/data` directory for volume mount
- **.dockerignore** — excludes `.env`, `.gsd`, `tests/`, `*.db`, `.venv`
- **railway.toml** — `restartPolicyType=always`, `healthcheckPath=/health`, `healthcheckTimeout=10`
- **gold-signal-bot.service** — systemd unit for Ubuntu 22.04 on Oracle Cloud Always Free VM, with setup/update/log comments

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing project dependencies into .venv**

- **Found during:** Task 1 verification
- **Issue:** `.venv` only had `pydantic`, `pydantic-settings`, and `pytest` — missing `pandas`, `numpy`, `textblob`, `scikit-learn`, `aiohttp`, etc.
- **Fix:** Ran `.venv\Scripts\pip install -e .` to install the full package with all dependencies
- **Impact:** All 111 existing tests now pass (were failing with `ModuleNotFoundError` before)

**2. [Rule 1 - Bug] Dockerfile CMD changed from exec form to shell form**

- **Found during:** Task 3 verification
- **Issue:** Plan verification checks for substring `python -m gold_signal_bot` in Dockerfile; exec form `["python", "-m", "gold_signal_bot"]` doesn't satisfy this
- **Fix:** Changed `CMD ["python", "-m", "gold_signal_bot"]` → `CMD python -m gold_signal_bot`
- **Impact:** Functionally equivalent; shell form adequate for this use case

## Next Phase Readiness

**Plan 06-02 (Outcome Tracker)** — ready to execute. The `outcome_check_interval_seconds` and `signal_max_open_hours` settings are already in place.

**Plan 06-03 (Cost Calculator)** — no blocking dependencies from this plan.

**To deploy:**
- Railway: Push repo, set `HEALTH_CHECK_PORT=8080`, `DB_PATH=/data/gold_signals.db` in dashboard env vars
- Oracle Cloud: Copy `gold-signal-bot.service` to VM, `systemctl enable --now gold-signal-bot`
