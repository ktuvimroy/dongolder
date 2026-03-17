"""SQLite repository for persisting sent trading signals and their outcomes.

Provides SignalRecord dataclass and SignalHistoryRepository that auto-creates
the signal_history table on first use. Used by AlertManager (write) and
OutcomeChecker (read/update) and stats commands (read).
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SignalRecord:
    """Maps 1:1 to a signal_history DB row.

    Nullable outcome fields are None until the signal is resolved.
    """

    signal_id: str          # UUID, unique PK
    sent_at: datetime       # UTC
    direction: str          # 'BUY' or 'SELL'
    timeframe: str          # 'H1', 'H4', 'D'
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    confidence: float       # 0.0–1.0
    reasoning: str          # JSON string of list[str]
    sentiment_factor: str | None
    ml_factor: str | None
    status: str = "OPEN"                    # 'OPEN', 'WIN', 'LOSS', 'EXPIRED'
    outcome_price: float | None = None
    outcome_at: datetime | None = None
    outcome_pnl_pct: float | None = None
    max_hours_open: int = 48
    id: int | None = None                   # DB autoincrement PK (None before insert)


class SignalHistoryRepository:
    """Repository for storing and retrieving signal history.

    Auto-creates the signal_history table on initialization.
    Uses parameterized queries to prevent SQL injection.

    Example:
        repo = SignalHistoryRepository("gold_signals.db")
        repo.save_signal(record)
        open_signals = repo.get_open_signals()
        stats = repo.get_stats()
    """

    def __init__(self, db_path: str | Path = "gold_signals.db") -> None:
        self.db_path = str(db_path)
        self._create_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_table(self) -> None:
        """Create signal_history table and indexes if they don't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    sent_at TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit_1 REAL NOT NULL,
                    take_profit_2 REAL,
                    confidence REAL NOT NULL,
                    reasoning TEXT NOT NULL,
                    sentiment_factor TEXT,
                    ml_factor TEXT,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    outcome_price REAL,
                    outcome_at TEXT,
                    outcome_pnl_pct REAL,
                    max_hours_open INTEGER NOT NULL DEFAULT 48
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sh_status
                ON signal_history(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sh_sent_at
                ON signal_history(sent_at)
            """)
            conn.commit()
        finally:
            conn.close()

    def save_signal(self, record: SignalRecord) -> None:
        """INSERT OR IGNORE a new OPEN signal.

        Idempotent on signal_id — safe to call multiple times.
        reasoning must already be a JSON string before calling this method.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO signal_history (
                    signal_id, sent_at, direction, timeframe,
                    entry_price, stop_loss, take_profit_1, take_profit_2,
                    confidence, reasoning, sentiment_factor, ml_factor,
                    status, max_hours_open
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.signal_id,
                    record.sent_at.isoformat(),
                    record.direction,
                    record.timeframe,
                    record.entry_price,
                    record.stop_loss,
                    record.take_profit_1,
                    record.take_profit_2,
                    record.confidence,
                    record.reasoning,
                    record.sentiment_factor,
                    record.ml_factor,
                    record.status,
                    record.max_hours_open,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_open_signals(self) -> list[SignalRecord]:
        """Return all rows where status='OPEN', ordered by sent_at ASC."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM signal_history
                WHERE status = 'OPEN'
                ORDER BY sent_at ASC
                """
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_outcome(
        self,
        signal_id: str,
        status: str,
        outcome_price: float,
        pnl_pct: float,
    ) -> None:
        """UPDATE signal_history SET status, outcome_price, outcome_at, outcome_pnl_pct."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE signal_history
                SET status = ?,
                    outcome_price = ?,
                    outcome_at = ?,
                    outcome_pnl_pct = ?
                WHERE signal_id = ?
                """,
                (
                    status,
                    outcome_price,
                    datetime.utcnow().isoformat(),
                    pnl_pct,
                    signal_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent(self, limit: int = 10) -> list[SignalRecord]:
        """Return last `limit` signals ordered by sent_at DESC (all statuses)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM signal_history
                ORDER BY sent_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Return aggregate performance statistics.

        Returns a dict with keys:
            total, wins, losses, expired, open_count, win_rate_pct,
            avg_pnl_pct, best_pnl_pct, worst_pnl_pct
        All fields default to 0 when the table is empty.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='WIN'  THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN status='EXPIRED' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_count,
                    ROUND(100.0 * SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN status IN ('WIN','LOSS') THEN 1 ELSE 0 END), 0),
                          1) as win_rate_pct,
                    ROUND(AVG(CASE WHEN status IN ('WIN','LOSS','EXPIRED')
                              THEN outcome_pnl_pct END) * 100, 2) as avg_pnl_pct,
                    ROUND(MAX(outcome_pnl_pct) * 100, 2) as best_pnl_pct,
                    ROUND(MIN(outcome_pnl_pct) * 100, 2) as worst_pnl_pct
                FROM signal_history
                """
            )
            row = cursor.fetchone()
            if row is None:
                return self._empty_stats()
            return {
                "total": row["total"] or 0,
                "wins": row["wins"] or 0,
                "losses": row["losses"] or 0,
                "expired": row["expired"] or 0,
                "open_count": row["open_count"] or 0,
                "win_rate_pct": row["win_rate_pct"] or 0,
                "avg_pnl_pct": row["avg_pnl_pct"] or 0,
                "best_pnl_pct": row["best_pnl_pct"] or 0,
                "worst_pnl_pct": row["worst_pnl_pct"] or 0,
            }
        finally:
            conn.close()

    def get_stats_by_timeframe(self) -> list[dict]:
        """Return per-timeframe performance stats.

        Returns list of dicts with keys: timeframe, total, wins, losses, win_rate_pct
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    timeframe,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='WIN'  THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
                    ROUND(100.0 * SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN status IN ('WIN','LOSS') THEN 1 ELSE 0 END), 0),
                          1) as win_rate_pct
                FROM signal_history
                GROUP BY timeframe
                ORDER BY timeframe
                """
            )
            return [
                {
                    "timeframe": row["timeframe"],
                    "total": row["total"] or 0,
                    "wins": row["wins"] or 0,
                    "losses": row["losses"] or 0,
                    "win_rate_pct": row["win_rate_pct"] or 0,
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> SignalRecord:
        """Convert a DB row to a SignalRecord."""
        outcome_at = None
        if row["outcome_at"]:
            outcome_at = datetime.fromisoformat(row["outcome_at"])
        return SignalRecord(
            id=row["id"],
            signal_id=row["signal_id"],
            sent_at=datetime.fromisoformat(row["sent_at"]),
            direction=row["direction"],
            timeframe=row["timeframe"],
            entry_price=row["entry_price"],
            stop_loss=row["stop_loss"],
            take_profit_1=row["take_profit_1"],
            take_profit_2=row["take_profit_2"],
            confidence=row["confidence"],
            reasoning=row["reasoning"],  # kept as JSON string
            sentiment_factor=row["sentiment_factor"],
            ml_factor=row["ml_factor"],
            status=row["status"],
            outcome_price=row["outcome_price"],
            outcome_at=outcome_at,
            outcome_pnl_pct=row["outcome_pnl_pct"],
            max_hours_open=row["max_hours_open"],
        )

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "expired": 0,
            "open_count": 0,
            "win_rate_pct": 0,
            "avg_pnl_pct": 0,
            "best_pnl_pct": 0,
            "worst_pnl_pct": 0,
        }
