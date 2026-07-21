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
    
class ValueBag:
    """Shared behaviour for anything backed by a dict of field values.

    Session and SimProfile both store free-text answers keyed by FieldSpec,
    so the reading and rendering logic lives here once. Exporters accept any
    ValueBag, which is why the same four formats work for sessions and for
    the Sim roster.
    """

    values: dict[str, str]

    def get(self, key: str) -> str:
        return (self.values.get(key) or "").strip()

    def is_empty(self) -> bool:
        """True when the player filled in nothing at all."""
        return not any(v.strip() for v in self.values.values())

    def as_blocks(self, fields: list[FieldSpec]) -> list[tuple[str, str]]:
        """(label, value) pairs for every field actually filled in."""
        return [(f.label, self.get(f.key)) for f in fields if self.get(f.key)]

    @staticmethod
    def _truncate(text: str, limit: int = 40) -> str:
        return text if len(text) <= limit else text[:limit - 3] + "…"


@dataclass
class Session(ValueBag):
    """One logged play session."""

    values: dict[str, str] = field(default_factory=dict)
    logged_at: dt.datetime = field(default_factory=dt.datetime.now)
    played_minutes: int | None = None
    id: int | None = None

    # queries

    def summary_line(self, fields: list[FieldSpec]) -> str:
        """Short one-line description for list views."""
        headline = next(
            (self.get(f.key) for f in fields if self.get(f.key)), "—"
        )
        return f"{self.logged_at:%Y-%m-%d %H:%M}  ·  {self._truncate(headline)}"

    @property
    def playtime_text(self) -> str:
        if self.played_minutes is None:
            return ""
        hours, minutes = divmod(self.played_minutes, 60)
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"

    # rendering

    def to_markdown(self, fields: list[FieldSpec]) -> str:
        lines = [f"## {self.logged_at:%Y-%m-%d %H:%M}"]
        if self.playtime_text:
            lines.append(f"*Played for {self.playtime_text}*")
        lines.append("")
        for label, value in self.as_blocks(fields):
            lines.append(f"**{label}**")
            lines.append(value)
            lines.append(f"")
        return "\n".join(lines)


@dataclass
class SimProfile(ValueBag):
    """One Sim or household in the story bible.

    Deliberately the same shape as Session: free-text values keyed by
    configurable FieldSpecs. That means the form builder, the repository's
    schema migration, and all four exporters work on Sims with no changes.
    """

    values: dict[str, str] = field(default_factory=dict)
    updated_at: dt.datetime = field(default_factory=dt.datetime.now)
    id: int | None = None

    NAME_KEY = "name"
    GROUP_KEY = "household"

    @property
    def display_name(self) -> str:
        return self.get(self.NAME_KEY) or "(unnamed Sim)"

    @property
    def household(self) -> str:
        return self.get(self.GROUP_KEY) or "No household"

    def summary_line(self, fields: list[FieldSpec] | None = None) -> str:
        """Name plus whatever short context is available."""
        bits = [self.get("generation"), self.get("story_role")]
        context = " · ".join(b for b in bits if b)
        return (f"{self.display_name}  ·  {self._truncate(context, 30)}"
                if context else self.display_name)

    def to_markdown(self, fields: list[FieldSpec]) -> str:
        lines = [f"## {self.display_name}"]
        subtitle = " · ".join(
            b for b in (self.get("household"), self.get("generation"),
                        self.get("story_role")) if b
        )
        if subtitle:
            lines.append(f"*{subtitle}*")
        lines.append("")
        for label, value in self.as_blocks(fields):
            if label.lower() == "sim name":
                continue          # already the heading
            lines.append(f"**{label}**")
            lines.append(value)
            lines.append("")
        return "\n".join(lines)
