"""Locating bundled assets.

PyInstaller unpacks a one-file build into a temporary directory and points
sys._MEIPASS at it, so the path to an asset differs between running from
source and running the frozen binary. This class hides that difference.
"""

from __future__ import annotations
import sys
from pathlib import Path


class Assets:
    """Finds files that ship with the app, frozen or not."""

    FOLDER = "assets"

    @classmethod
    def base_dir(cls) -> Path:
        bundled = getattr(sys, "_MEIPASS", None)
        if bundled:                              # running as a frozen exe
            return Path(bundled)
        # running from source: repo root is one level above the package
        return Path(__file__).resolve().parent.parent

    @classmethod
    def path(cls, name: str) -> Path | None:
        """Absolute path to an asset, or None if it isn't there.

        Returns None rather than raising: a missing icon should never stop
        the app from opening.
        """
        candidate = cls.base_dir() / cls.FOLDER / name
        if candidate.exists():
            return candidate
        # Frozen builds may flatten the folder away.
        flat = cls.base_dir() / name
        return flat if flat.exists() else None

    @classmethod
    def icon_png(cls) -> Path | None:
        return cls.path("icon.png")
