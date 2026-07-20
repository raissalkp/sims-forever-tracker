""" Persistance layer.

SessionRespository owns every SQL statement in the app. Nothing else touches
the database, so swapping storage later would mean rewriting only this file.
"""

from __future__ import annotations
import datetime as dt
import sqlite3
from pathlib import Path
from .models import FieldSpec, Session

RESERVED = {"id", "logged_at", "played_minutes"}


class SessionRepository:
    """Stores and retrives Session objects."""

    def __init__(self, db_path: Path, fields: list[FieldSpec]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fields = [f for f in fields if f.key not in RESERVED]
        self._ensure_schema()

    # schema

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_schema(self) -> None:
        """Create the table, then add the colums for any newly configured field.

        This is what lets the players add their own questions to config.json
        without losing existing entries        
        """
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sessions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at TEXT NOT NULL,
                    played_minutes INTEGER
                )"""
            )
            existing ={
                row["name"]
                for row in conn.execute("PRAGMA table_info(sessions)")
            }
            for spec in self.fields:
                if spec.key not in existing:
                    conn.execute(
                        f"ALTER TABLE sessions ADD COLUMN {spec.key} TEXT"
                    )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_logged_at "
                "ON sessions (logged_at DESC)"
            )
    
    def _column_names(self) -> list[str]:
        with self._connect() as conn:
            return [
                row["name"]
                for row in conn.execute("PRAGMA table_info(sessions)")
            ]
    
    # mapping

    def _to_session(self, row: sqlite3.Row) -> Session:
        data = dict(row)
        try:
            logged_at = dt.datetime.fromisoformat(data["logged_at"])
        except (ValueError, TypeError):
            logged_at = dt.datetime.now()
        values = {
            key: (value or "")
            for key, value in data.items()
            if key not in RESERVED
        }
        return Session(
            id=data.get("id"),
            logged_at=logged_at,
            played_minutes=data.get("played_minutes"),
            values=values,
        )
    
    # commands

    def add(self, session:Session) -> Session:
        columns = [f.key for f in self.fields if f.key in self._column_names()]
        placeholders = ", ".join("?" for _ in range(len(columns) + 2))
        sql = (
            f"INSERT INTO sessions (logged_at, played_minutes"
            f"{''.join(', ' + c for c in columns)}) VALUES ({placeholders})"
        )
        params = [session.logged_at.isoformat(timespec="minutes"),
                  session.played_minutes]
        params += [session.get(c) for c in columns]
        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            session.id = cursor.lastrowid
        return session

    def delete(self, session_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # queries

    def latest(self) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._to_session(row) if row else None
    
    def all(self) -> list[Session]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC"
            ).fetchall()
        return [self._to_session(r) for r in rows]
    
    def search(self, term: str) -> list[Session]:
        """Case insensitive substring search across every text field"""
        term = term.strip().lower()
        if not term:
            return self.all()
        return [
            s for s in self.all()
            if any(term in (v or "").lower() for v in s.values.values())
        ]
    
    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        
    def total_minutes(self) -> int:
        with self._connect() as conn:
            value = conn.execute(
                "SELECT COALESCE(SUM(played_minutes), 0) FROM sessions"
            ).fetchone()[0]
        return int(value or 0)
