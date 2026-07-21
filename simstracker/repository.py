"""Persistence layer.

Every SQL statement in the app lives here. Nothing else touches the
database, so swapping storage later would mean rewriting only this file.

TableRepository holds the parts that don't care what's being stored: the
connection, the schema migration that lets players add their own questions
to config.json without losing data, and the generic queries. SessionRepository
and SimRepository subclass it and supply their table name, their reserved
columns, and how to turn a row into a domain object.
"""

from __future__ import annotations
import datetime as dt
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from .models import FieldSpec, Session, SimProfile


class TableRepository(ABC):
    """Shared storage behaviour for one table of value-bag records."""

    table: str = ""
    reserved: set[str] = set()
    order_by: str = "id DESC"

    def __init__(self, db_path: Path, fields: list[FieldSpec]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fields = [f for f in fields if f.key not in self.reserved]
        self._ensure_schema()

    # subclass hooks

    @abstractmethod
    def _base_columns(self) -> str:
        """SQL for the columns this table always has, beyond id."""

    @abstractmethod
    def _to_record(self, row: sqlite3.Row):
        """Turn a database row into a domain object."""

    @abstractmethod
    def _insert_values(self, record) -> tuple[list[str], list]:
        """Return (base column names, base values) for an insert."""

    # schema

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create the table, then add a column for any newly configured field.

        This is what lets players add their own questions to config.json
        without losing existing entries.
        """
        with self._connect() as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        {self._base_columns()}
                    )"""
            )
            existing = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({self.table})")
            }
            for spec in self.fields:
                if spec.key not in existing:
                    conn.execute(
                        f"ALTER TABLE {self.table} ADD COLUMN {spec.key} TEXT"
                    )

    def _column_names(self) -> list[str]:
        with self._connect() as conn:
            return [
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({self.table})")
            ]

    def _value_columns(self) -> list[str]:
        present = set(self._column_names())
        return [f.key for f in self.fields if f.key in present]

    # commands

    def add(self, record):
        base_cols, base_vals = self._insert_values(record)
        cols = base_cols + self._value_columns()
        placeholders = ", ".join("?" for _ in cols)
        sql = (f"INSERT INTO {self.table} ({', '.join(cols)}) "
               f"VALUES ({placeholders})")
        params = base_vals + [record.get(c) for c in self._value_columns()]
        with self._connect() as conn:
            record.id = conn.execute(sql, params).lastrowid
        return record

    def update(self, record):
        """Write an existing record back. Falls through to add() if new."""
        if record.id is None:
            return self.add(record)
        base_cols, base_vals = self._insert_values(record)
        cols = base_cols + self._value_columns()
        assignments = ", ".join(f"{c} = ?" for c in cols)
        params = base_vals + [record.get(c) for c in self._value_columns()]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table} SET {assignments} WHERE id = ?",
                params + [record.id],
            )
        return record

    def delete(self, record_id: int) -> None:
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self.table} WHERE id = ?",
                         (record_id,))

    # queries

    def all(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.table} ORDER BY {self.order_by}"
            ).fetchall()
        return [self._to_record(r) for r in rows]

    def latest(self):
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table} ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._to_record(row) if row else None

    def get_by_id(self, record_id: int):
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table} WHERE id = ?", (record_id,)
            ).fetchone()
        return self._to_record(row) if row else None

    def search(self, term: str) -> list:
        """Case-insensitive substring search across every text field."""
        term = term.strip().lower()
        if not term:
            return self.all()
        return [
            r for r in self.all()
            if any(term in (v or "").lower() for v in r.values.values())
        ]

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM {self.table}"
            ).fetchone()[0]

    @staticmethod
    def _parse_time(value) -> dt.datetime:
        try:
            return dt.datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return dt.datetime.now()


class SessionRepository(TableRepository):
    """Stores and retrieves Session objects."""

    table = "sessions"
    reserved = {"id", "logged_at", "played_minutes"}

    def _base_columns(self) -> str:
        return "logged_at TEXT NOT NULL, played_minutes INTEGER"

    def _to_record(self, row: sqlite3.Row) -> Session:
        data = dict(row)
        return Session(
            id=data.get("id"),
            logged_at=self._parse_time(data.get("logged_at")),
            played_minutes=data.get("played_minutes"),
            values={k: (v or "") for k, v in data.items()
                    if k not in self.reserved},
        )

    def _insert_values(self, record: Session) -> tuple[list[str], list]:
        return (
            ["logged_at", "played_minutes"],
            [record.logged_at.isoformat(timespec="minutes"),
             record.played_minutes],
        )

    def total_minutes(self) -> int:
        with self._connect() as conn:
            value = conn.execute(
                "SELECT COALESCE(SUM(played_minutes), 0) FROM sessions"
            ).fetchone()[0]
        return int(value or 0)


class SimRepository(TableRepository):
    """Stores and retrieves SimProfile objects — the story bible."""

    table = "sims"
    reserved = {"id", "updated_at"}
    # Sims read best grouped by family, then in generation order.
    order_by = "household COLLATE NOCASE, generation COLLATE NOCASE, id"

    def _base_columns(self) -> str:
        return "updated_at TEXT NOT NULL"

    def _to_record(self, row: sqlite3.Row) -> SimProfile:
        data = dict(row)
        return SimProfile(
            id=data.get("id"),
            updated_at=self._parse_time(data.get("updated_at")),
            values={k: (v or "") for k, v in data.items()
                    if k not in self.reserved},
        )

    def _insert_values(self, record: SimProfile) -> tuple[list[str], list]:
        record.updated_at = dt.datetime.now()
        return (["updated_at"],
                [record.updated_at.isoformat(timespec="minutes")])

    def _ensure_schema(self) -> None:
        super()._ensure_schema()
        # order_by references these, so they must exist even if a player
        # removes them from their configured fields.
        with self._connect() as conn:
            existing = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({self.table})")
            }
            for column in ("household", "generation"):
                if column not in existing:
                    conn.execute(
                        f"ALTER TABLE {self.table} ADD COLUMN {column} TEXT"
                    )

    def households(self) -> list[str]:
        """Distinct household names, in display order."""
        seen: list[str] = []
        for sim in self.all():
            if sim.household not in seen:
                seen.append(sim.household)
        return seen
