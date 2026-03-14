"""SQLite repositories for price data storage.

This module provides repository classes for persisting spot prices
and OHLC candles to SQLite database. Tables are auto-created on first use.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from .models import OHLC, SpotPrice, Timeframe


class SpotPriceRepository:
    """Repository for storing and retrieving spot prices.
    
    Auto-creates the spot_prices table on initialization.
    Uses parameterized queries to prevent SQL injection.
    
    Example:
        repo = SpotPriceRepository("gold_data.db")
        spot = SpotPrice(timestamp=datetime.utcnow(), price=2050.50)
        repo.save(spot)
        recent = repo.get_latest(limit=10)
    """
    
    def __init__(self, db_path: str | Path = "gold_data.db") -> None:
        """Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file. Use ":memory:" for testing.
        """
        self.db_path = str(db_path)
        self._create_table()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_table(self) -> None:
        """Create spot_prices table if it doesn't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spot_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    UNIQUE(timestamp)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spot_timestamp 
                ON spot_prices(timestamp)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def save(self, spot: SpotPrice) -> None:
        """Insert a spot price record.
        
        Uses INSERT OR IGNORE to avoid duplicate timestamp errors.
        
        Args:
            spot: SpotPrice instance to persist.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO spot_prices (timestamp, price)
                VALUES (?, ?)
                """,
                (spot.timestamp.isoformat(), spot.price)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_range(self, start: datetime, end: datetime) -> list[SpotPrice]:
        """Get spot prices within a time range.
        
        Args:
            start: Start of range (inclusive).
            end: End of range (inclusive).
            
        Returns:
            List of SpotPrice objects ordered by timestamp ascending.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT timestamp, price FROM spot_prices
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (start.isoformat(), end.isoformat())
            )
            return [
                SpotPrice(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    price=row["price"]
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def get_latest(self, limit: int = 100) -> list[SpotPrice]:
        """Get most recent spot prices.
        
        Args:
            limit: Maximum number of records to return.
            
        Returns:
            List of SpotPrice objects ordered by timestamp descending.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT timestamp, price FROM spot_prices
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [
                SpotPrice(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    price=row["price"]
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()


class OHLCRepository:
    """Repository for storing and retrieving OHLC candles.
    
    Auto-creates the ohlc_candles table on initialization.
    Supports upsert (update if exists, insert if new) for candle updates.
    
    Example:
        repo = OHLCRepository("gold_data.db")
        candle = OHLC(
            timestamp=datetime.utcnow(),
            open=2050.0, high=2055.0, low=2048.0, close=2053.0,
            timeframe=Timeframe.H1
        )
        repo.save(candle)
        hourly = repo.get_latest(Timeframe.H1, limit=24)
    """
    
    def __init__(self, db_path: str | Path = "gold_data.db") -> None:
        """Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file. Use ":memory:" for testing.
        """
        self.db_path = str(db_path)
        self._create_table()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_table(self) -> None:
        """Create ohlc_candles table if it doesn't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlc_candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    timeframe TEXT NOT NULL,
                    UNIQUE(timestamp, timeframe)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlc_timeframe_timestamp 
                ON ohlc_candles(timeframe, timestamp)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def save(self, candle: OHLC) -> None:
        """Insert or update an OHLC candle.
        
        Uses INSERT OR REPLACE to upsert by (timestamp, timeframe).
        This allows updating in-progress candles as new prices arrive.
        
        Args:
            candle: OHLC instance to persist.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO ohlc_candles 
                (timestamp, open, high, low, close, timeframe)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candle.timestamp.isoformat(),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.timeframe.value
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_latest(self, timeframe: Timeframe, limit: int = 100) -> list[OHLC]:
        """Get most recent candles for a timeframe.
        
        Args:
            timeframe: Candle timeframe to query.
            limit: Maximum number of candles to return.
            
        Returns:
            List of OHLC objects ordered by timestamp descending.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT timestamp, open, high, low, close, timeframe 
                FROM ohlc_candles
                WHERE timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (timeframe.value, limit)
            )
            return [
                OHLC(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    timeframe=Timeframe(row["timeframe"])
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
    
    def get_range(
        self, 
        timeframe: Timeframe, 
        start: datetime, 
        end: datetime
    ) -> list[OHLC]:
        """Get candles within a time range.
        
        Args:
            timeframe: Candle timeframe to query.
            start: Start of range (inclusive).
            end: End of range (inclusive).
            
        Returns:
            List of OHLC objects ordered by timestamp ascending.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT timestamp, open, high, low, close, timeframe 
                FROM ohlc_candles
                WHERE timeframe = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (timeframe.value, start.isoformat(), end.isoformat())
            )
            return [
                OHLC(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    timeframe=Timeframe(row["timeframe"])
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
