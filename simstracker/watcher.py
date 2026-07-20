"""Game detection.

GameWatcher polls the process table and fires callsback on launch and exit.
It knows nothing about the UI, the app wires callbacks to windows.
"""

from __future__ import annotations
import datetime as dt
import logging
import os
import time
from pathlib import Path
from typing import Callable

try:
    import psutil
except ImportError as exc: #pragma: no cover
    raise SystemExit("psutil is required: pip install psutil") from exc

log = logging.getLogger(__name__)

Callback = Callable[[], None]
ExitCallback = Callable[[int | None], None]


class SingleInstanceLock:
    """Stops two watchers running at once e.g. autostart + manual launch
    
    Uses a PID file rather than an OS mutex so it behaves the same on
    Windows and macOS, self-heals if a previous run was killed.
    """

    def __init__(self, path: Path, marker: str = "simstracker") -> None:
        self.path = Path(path)
        self.marker = marker
        self.acquired = False
        self.holder_pid: int | None = None

    @staticmethod
    def _normalise(text: str) -> str:
        """Strip everything but letters and digits, so 'sims_tracker.py',
        'SimsTracker.exe', and 'simstracker' all compare equal."""
        return "".join(c for c in text.lower() if c.isalnum())

    def _is_live_holder(self, pid: int) -> bool:
        """True only if that PID is running AND looks like this app.

        Checking the name as well as the PID matters because operating
        systems recycle PIDs aggressively. Without this, an unrelated
        process inheriting the number would lock the player out of their
        own app permanently, with no fix but deleting the file by hand.
        """
        if pid <= 0 or not psutil.pid_exists(pid):
            return False
        try:
            proc = psutil.Process(pid)
            haystack = self._normalise(" ".join([proc.name(), *proc.cmdline()]))
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            # Can't inspect it — assume it is ours and stay cautious.
            return True
        return self._normalise(self.marker) in haystack

    def acquire(self) -> bool:
        if self.path.exists():
            try:
                pid = int(self.path.read_text().strip())
            except (ValueError, OSError):
                pid = -1
            if self._is_live_holder(pid):
                self.holder_pid = pid
                return False
            self.path.unlink(missing_ok=True)
        try:
            self.path.write_text(str(os.getpid()))
        except OSError:
            return True
        self.acquired = True
        return True
    
    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self) -> "SingleInstanceLock":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()

class GameWatcher:
    """Polls for the game process and reports launches and exits."""

    def __init__(
        self,
        process_names: list[str],
        poll_seconds: int = 10,
        on_launch: Callback | None = None,
        on_exit: ExitCallback | None = None,
    ) -> None:
        self.process_names = {n.lower() for n in process_names}
        self.poll_seconds = max(2, poll_seconds)
        self.on_launch = on_launch
        self.on_exit = on_exit
        self._running = False
        self._stop = False
        self._started_at: dt.datetime | None = None

    # detection

    def is_game_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info["name"] or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in self.process_names:
                return True
            if any(name.startswith(known) for known in self.process_names):
                return True
        return False
    
    @classmethod
    def detect_candidates(
        cls, keywords: tuple[str, ...] = ("ts4", "sims"),
        exclude: tuple[str, ...] = ("simstracker",),
    ) -> list[str]:
        """Return names of running processes that look like the game.

        Powers the "Detect my game" button. The Sims ships several
        executables depending on renderer (DX11 vs DX9) and platform, and
        players have no way of knowing which one they are running, so
        guessing on their behalf is friendlier than asking them to open
        Task Manager.
        """
        found: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                raw = proc.info["name"] or ""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            lowered = raw.lower()
            if any(skip in lowered.replace("_", "") for skip in exclude):
                continue
            if any(word in lowered for word in keywords):
                found.add(lowered)
        return sorted(found)

    @property
    def session_minutes(self) -> int | None:
        if self._started_at is None:
            return None
        delta = dt.datetime.now() - self._started_at
        return max(0, int(delta.total_seconds() // 60))
    
    # loop

    def poll_once(self) -> None:
        """One detection tick. Seperated so tests can drive it"""
        now_running = self.is_game_running()
        if now_running and not self._running:
            self._started_at = dt.datetime.now()
            log.info("The Sims 4 launched.")
            if self.on_launch:
                self.on_launch()
        elif self._running and not now_running:
            minutes = self.session_minutes
            self._started_at = None
            log.info("The Sims 4 exited after %s minutes.", minutes)
            if self.on_exit:
                self.on_exit(minutes)
        self._running = now_running

    def prime(self) -> None:
        """Record the game's current state without firing callbacks.
        
        Called at startup so launching the tracker while the game is already
        open doesn't immediately pop a recap window over the top of it
        """

        self._running = self.is_game_running()
        if self._running:
            self._started_at = dt.datetime.now()
            log.info("Game already running at startup; not showing recap")
    
    def run(self) -> None:
        self._stop = False
        self.prime()
        log.info("Watching for The Sims 4 (every %ss).", self.poll_seconds)
        while not self._stop:
            time.sleep(self.poll_seconds)
            try:
                self.poll_once()
            except Exception: #pragma not cover never kill the watcher
                log.exception("Error during poll; continuing.")

    def stop(self) -> None:
        self._stop = True