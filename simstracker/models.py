""" Domain models for Sims Forever Tracker.

These classes describe what a session is and what the log form asks,
with no knowledge of storage or UI.
"""

from __future__ import annotations
import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass(frozen=True)
class FieldSpec:
    """Describes one question on the session log form.

    The form, the database schema, and every export are all generated from 
    a list of these, so adding a question is a one line change.
    """

    key: str
    label: str
    multiline: bool = False
    prefill_from_last: bool = False
    help_text: str = ""

    def __post_init__(self) -> None:
        if not self.key.isidentifier():
            raise ValueError(
                f"Field key {self.key!r} must be a valid identifier "
                "(letters, digits, underscores; no spaces)."
            )
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldSpec":
        return cls(
            key=data["key"],
            label=data.get("label", data["key"].replace("_", " ").title()),
            multiline=bool(data.get("multiline", False)),
            prefill_from_last=bool(data.get("prefill_from_last", False)),
            help_text=data.get("help_text", "",)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
@dataclass
class Session: 
    """One logged play session."""

    values: dict[str, str] = field(default_factory=dict)
    logged_at: dt.datetime = field(default_factory=dt.datetime.now)
    played_minutes: int | None = None
    id: int | None = None
    # queries

    def get(self, key: str) -> str:
        return (self.values.get(key) or "").strip()
    
    def is_empty(self) -> bool:
        """True when the player filled in nothing at all"""
        return not any(v.strip() for v in self.values.values())
    
    def summary_line(self, fields: list[FieldSpec]) -> str:
        """Short one line description for list views"""
        headline = next(
            (self.get(f.key) for f in fields if self.get(f.key)), "_"
        )
        if len(headline) > 40:
            headline = headline[:37] + "..."
        return f"{self.logged_at:%Y-%m-%d %H:%M}    ·   {headline}"
    
    @property
    def playtime_text(self) -> str:
        if self.played_minutes is None:
            return ""
        hours, minutes = divmod(self.played_minutes, 60)
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"
    
    # rendering

    def as_blocks(self, fields: list[FieldSpec]) -> list[tuple[str, str]]:
        """(label, value) pairs foe every field the player actually filled"""
        return [(f.label, self.get(f.key)) for f in fields if self.get(f.key)]
    
    def to_markdown(self, fields: list[FieldSpec]) -> str:
        lines = [f"## {self.logged_at:%Y-%m-%d %H%M}"]
        if self.playtime_text:
            lines.append(f"*Played for {self.playtime_text}")
        lines.append("")
        for label, value in self.as_blocks(fields):
            lines.append(f"**{label}**")
            lines.append(value)
            lines.append(f"")
        return "\n".join(lines)
