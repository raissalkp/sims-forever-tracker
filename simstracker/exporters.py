"""Exporters.

A small strategy hierarchy: each subclass knows one output format. The app
picks one by name, so adding a format means adding a class and registering it.
"""

from __future__ import annotations
import csv
import io
import json
from abc import ABC, abstractmethod
from .models import FieldSpec, Session, SimProfile


class Exporter(ABC):
    """Base class for every export format."""

    name: str = ""
    extension: str = ".txt"

    def __init__(self, fields: list[FieldSpec]) -> None:
        self.fields = fields

    @abstractmethod
    def render(self, sessions: list[Session]) -> str:
        """Return the whole export as a string."""


class MarkdownExporter(Exporter):
    """Notion-friendly: paste straight into a page."""

    name = "markdown"
    extension = ".md"

    def render(self, sessions: list[Session]) -> str:
        if not sessions:
            return "# Sims Forever Tracker\n\nNothing recorded yet.\n"
        is_roster = isinstance(sessions[0], SimProfile)
        heading = ("# Sims Forever Tracker — Sim roster" if is_roster
                   else "# Sims Forever Tracker — session journal")
        parts = [heading, ""]
        ordered = sessions if is_roster else list(reversed(sessions))
        for session in ordered:   # sessions oldest-first, so they read as a story
            parts.append(session.to_markdown(self.fields))
            parts.append("---")
            parts.append("")
        return "\n".join(parts)


class TableExporter(Exporter):
    """One row per session — good for a Notion database import."""

    name = "table"
    extension = ".md"

    def render(self, sessions: list[Session]) -> str:
        dated = bool(sessions) and hasattr(sessions[0], "logged_at")
        headers = (["Date"] if dated else []) + [f.label for f in self.fields]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for session in (reversed(sessions) if dated else sessions):
            cells = [f"{session.logged_at:%Y-%m-%d %H:%M}"] if dated else []
            cells += [
                session.get(f.key).replace("\n", "<br>").replace("|", "\\|")
                for f in self.fields
            ]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines) + "\n"


class CsvExporter(Exporter):
    name = "csv"
    extension = ".csv"

    def render(self, sessions: list[Session]) -> str:
        dated = bool(sessions) and hasattr(sessions[0], "logged_at")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            (["logged_at", "played_minutes"] if dated else [])
            + [f.key for f in self.fields]
        )
        for session in (reversed(sessions) if dated else sessions):
            base = ([session.logged_at.isoformat(timespec="minutes"),
                     session.played_minutes or ""] if dated else [])
            writer.writerow(base + [session.get(f.key) for f in self.fields])
        return buffer.getvalue()


class JsonExporter(Exporter):
    name = "json"
    extension = ".json"

    def render(self, sessions: list[Session]) -> str:
        dated = bool(sessions) and hasattr(sessions[0], "logged_at")

        def row(s):
            base = ({"logged_at": s.logged_at.isoformat(timespec="minutes"),
                     "played_minutes": s.played_minutes} if dated else {})
            return {**base, **{f.key: s.get(f.key) for f in self.fields}}

        ordered = reversed(sessions) if dated else sessions
        return json.dumps([row(s) for s in ordered], indent=2)


class ExporterRegistry:
    """Looks up an exporter by name."""

    _classes: list[type[Exporter]] = [
        MarkdownExporter, TableExporter, CsvExporter, JsonExporter
    ]

    def __init__(self, fields: list[FieldSpec]) -> None:
        self.fields = fields

    @classmethod
    def names(cls) -> list[str]:
        return [c.name for c in cls._classes]

    def get(self, name: str) -> Exporter:
        for klass in self._classes:
            if klass.name == name:
                return klass(self.fields)
        raise ValueError(
            f"Unknown format {name!r}. Choose from: {', '.join(self.names())}"
        )
