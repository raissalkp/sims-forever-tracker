"""User configuration.

Settings live in a JSON file next to the data directory so players never
have to edit source code (which also matters for the frozen .exe build,
where there *is* no source to edit).
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any
from .models import FieldSpec

APP_NAME = "SimsForeverTracker"

DEFAULT_PROCESS_NAMES = [
    "ts4_x64.exe",       # Windows, DX11 renderer (the usual one)
    "ts4_dx9_x64.exe",   # Windows, DX9 renderer (legacy mode / older GPUs)
    "ts4.exe",           # Windows, 32-bit / older installs
    "the sims 4",        # macOS
    "ts4_x64",           # macOS alternate
]

DEFAULT_FIELDS: list[dict[str, Any]] = [
    {"key": "household", "label": "Household played",
     "prefill_from_last": True},
    {"key": "sim_week", "label": "Sim-week / rotation #",
     "prefill_from_last": True},
    {"key": "major_events", "label": "Major events", "multiline": True,
     "help_text": "What actually happened this session?"},
    {"key": "deaths_births", "label": "Deaths / births / breakups",
     "multiline": True},
    {"key": "money_notes", "label": "Money (clean / dirty)"},
    {"key": "secrets_created", "label": "Secrets created", "multiline": True,
     "help_text": "Who now knows something they shouldn't?"},
    {"key": "secrets_at_risk", "label": "Secrets at risk", "multiline": True},
    {"key": "ripples", "label": "Ripple effects for other households",
     "multiline": True},
    {"key": "tragedy_roll", "label": "Curse / tragedy roll (if any)"},
    {"key": "next_time", "label": "Where I left off / do next time",
     "multiline": True,
     "help_text": "Future-you reads this first thing next session."},
]


DEFAULT_SIM_FIELDS: list[dict[str, Any]] = [
    {"key": "name", "label": "Sim name"},
    {"key": "household", "label": "Household / family",
     "prefill_from_last": True,
     "help_text": "Groups the roster. Vance, Osei, Hollow…"},
    {"key": "generation", "label": "Generation",
     "prefill_from_last": True, "help_text": "Gen 1, Gen 2…"},
    {"key": "story_role", "label": "Role in the story",
     "help_text": "Founder, heir, spare, antagonist, spouse…"},
    {"key": "status", "label": "Life stage / status",
     "help_text": "Teen, adult, elder, deceased, ghost…"},
    {"key": "traits", "label": "Traits", "multiline": True},
    {"key": "aspiration", "label": "Aspiration"},
    {"key": "career", "label": "Career / job"},
    {"key": "goals", "label": "Goals for this Sim", "multiline": True,
     "help_text": "What they must achieve before the generation ends."},
    {"key": "storyline", "label": "Storyline / arc", "multiline": True,
     "help_text": "Their beats from introduction to exit."},
    {"key": "secrets", "label": "Secrets they hold", "multiline": True,
     "help_text": "And who else knows."},
    {"key": "relationships", "label": "Key relationships", "multiline": True},
    {"key": "notes", "label": "Notes", "multiline": True},
]


def default_data_dir() -> Path:
    """Per-user data directory, following each platform's convention."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
        )
    return base / APP_NAME


class Config:
    """Loads, validates, and saves user settings."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "config.json"

        self.process_names: list[str] = list(DEFAULT_PROCESS_NAMES)
        self.poll_seconds: int = 10
        self.show_recap_on_launch: bool = True
        self.show_log_on_exit: bool = True
        self.recap_delay_seconds: int = 20
        self.theme: str = "dark"
        self._field_data: list[dict[str, Any]] = [
            dict(f) for f in DEFAULT_FIELDS
        ]
        self._sim_field_data: list[dict[str, Any]] = [
            dict(f) for f in DEFAULT_SIM_FIELDS
        ]

        if self.path.exists():
            self.load()
        else:
            self.save()

    # derived paths

    @property
    def db_path(self) -> Path:
        return self.data_dir / "sessions.db"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "tracker.log"

    @property
    def lock_path(self) -> Path:
        return self.data_dir / "tracker.lock"

    @property
    def fields(self) -> list[FieldSpec]:
        return [FieldSpec.from_dict(f) for f in self._field_data]

    @property
    def sim_fields(self) -> list[FieldSpec]:
        return [FieldSpec.from_dict(f) for f in self._sim_field_data]

    # persistence

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt config should never stop the app from running.
            return
        self.process_names = [
            str(n).lower() for n in
            data.get("process_names", self.process_names)
        ]
        self.poll_seconds = max(2, int(data.get("poll_seconds",
                                                self.poll_seconds)))
        self.show_recap_on_launch = bool(
            data.get("show_recap_on_launch", self.show_recap_on_launch))
        self.show_log_on_exit = bool(
            data.get("show_log_on_exit", self.show_log_on_exit))
        self.recap_delay_seconds = max(
            0, int(data.get("recap_delay_seconds", self.recap_delay_seconds)))
        self.theme = str(data.get("theme", self.theme))
        fields = data.get("fields")
        if isinstance(fields, list) and fields:
            self._field_data = fields
        sim_fields = data.get("sim_fields")
        if isinstance(sim_fields, list) and sim_fields:
            self._sim_field_data = sim_fields

    def add_process_names(self, names: list[str]) -> list[str]:
        """Record newly detected game executables. Returns the ones added."""
        added = [
            n.lower() for n in names
            if n and n.lower() not in self.process_names
        ]
        if added:
            self.process_names.extend(added)
            self.save()
        return added

    def save(self) -> None:
        payload = {
            "process_names": self.process_names,
            "poll_seconds": self.poll_seconds,
            "show_recap_on_launch": self.show_recap_on_launch,
            "show_log_on_exit": self.show_log_on_exit,
            "recap_delay_seconds": self.recap_delay_seconds,
            "theme": self.theme,
            "fields": self._field_data,
            "sim_fields": self._sim_field_data,
        }
        self.path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
