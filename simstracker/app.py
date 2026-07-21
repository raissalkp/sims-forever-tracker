"""Application orchestration and command-line interface."""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from .config import Config
from .exporters import ExporterRegistry
from .models import Session
from .repository import SessionRepository, SimRepository
from .ui import (HistoryWindow, HomeWindow, LogWindow,
                 RecapWindow, SimsWindow)
from .watcher import GameWatcher, SingleInstanceLock

__version__ = "1.2.0"

log = logging.getLogger("simstracker")


class TrackerApp:
    """Wires config, storage, watcher, and UI together."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.repository = SessionRepository(
            self.config.db_path, self.config.fields
        )
        self.sims = SimRepository(
            self.config.db_path, self.config.sim_fields
        )
        self.exporters = ExporterRegistry(self.config.fields)
        self.sim_exporters = ExporterRegistry(self.config.sim_fields)
        self.watcher = GameWatcher(
            process_names=self.config.process_names,
            poll_seconds=self.config.poll_seconds,
            on_launch=self.handle_launch,
            on_exit=self.handle_exit,
        )
        self._configure_logging()

    def _configure_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-7s %(message)s",
            handlers=[
                logging.FileHandler(self.config.log_path, encoding="utf-8"),
                # stderr, so `export | head` and shell pipes stay clean.
                logging.StreamHandler(sys.stderr),
            ],
        )

    # watcher callbacks

    def handle_launch(self) -> None:
        if self.config.show_recap_on_launch:
            self.show_recap()

    def handle_exit(self, played_minutes: int | None) -> None:
        if self.config.show_log_on_exit:
            self.show_log(played_minutes)

    # windows

    def _stats_line(self) -> str:
        count = self.repository.count()
        if not count:
            return ""
        hours = self.repository.total_minutes() // 60
        text = f"{count} session{'s' if count != 1 else ''} logged"
        if hours:
            text += f" · {hours}h tracked"
        sims = self.sims.count()
        if sims:
            text += f" · {sims} Sim{'s' if sims != 1 else ''} recorded"
        return text

    def show_recap(self) -> None:
        RecapWindow(
            session=self.repository.latest(),
            fields=self.config.fields,
            theme=self.config.theme,
            stats=self._stats_line(),
        ).show()

    def show_log(self, played_minutes: int | None = None) -> None:
        LogWindow(
            fields=self.config.fields,
            repository=self.repository,
            played_minutes=played_minutes,
            theme=self.config.theme,
            on_saved=lambda s: log.info("Session %s saved.", s.id),
        ).show()

    def show_home(self) -> None:
        """Show the home window and act on whatever the player picks.

        Loops so that closing the log or history window returns here
        rather than quitting the app outright.
        """
        while True:
            window = HomeWindow(
                session=self.repository.latest(),
                fields=self.config.fields,
                theme=self.config.theme,
                stats=self._stats_line(),
                watching=self.is_watcher_running(),
            )
            window.show()
            action = window.action

            if action == "log":
                self.show_log()
            elif action == "history":
                self.show_history()
            elif action == "sims":
                self.show_sims()
            elif action == "save_detected":
                added = self.config.add_process_names(window.detected)
                log.info("Added process names: %s", ", ".join(added) or "none")
                self.watcher.process_names = {
                    n.lower() for n in self.config.process_names
                }
            elif action == "watch":
                self.watch()
                return
            else:                      # window closed with no choice
                return

    def is_watcher_running(self) -> bool:
        """True if another instance already holds the watch lock."""
        probe = SingleInstanceLock(self.config.lock_path)
        if probe.acquire():
            probe.release()
            return False
        return True

    def show_sims(self) -> None:
        SimsWindow(
            repository=self.sims,
            fields=self.config.sim_fields,
            exporters=self.sim_exporters,
            theme=self.config.theme,
        ).show()

    def show_history(self) -> None:
        HistoryWindow(
            repository=self.repository,
            fields=self.config.fields,
            exporters=self.exporters,
            theme=self.config.theme,
        ).show()

    # commands

    def export(self, format_name: str, destination: Path | None,
               sims: bool = False) -> str:
        registry = self.sim_exporters if sims else self.exporters
        source = self.sims if sims else self.repository
        exporter = registry.get(format_name)
        content = exporter.render(source.all())
        if destination:
            destination = Path(destination)
            destination.write_text(content, encoding="utf-8")
            log.info("Exported %s records to %s",
                     source.count(), destination)
        return content

    def watch(self) -> None:
        with SingleInstanceLock(self.config.lock_path) as lock:
            if not lock.acquire():
                log.warning(
                    "Another Sims Forever Tracker is already watching "
                    "(pid %s). Showing the recap instead.", lock.holder_pid,
                )
                # Never exit silently: with --noconsole a second launch
                # would look like the app is broken. Hand the player the
                # home window instead and leave the original watcher
                # running untouched.
                self.show_home()
                return
            log.info("Sims Forever Tracker %s — data in %s",
                     __version__, self.config.data_dir)
            try:
                self.watcher.run()
            except KeyboardInterrupt:
                log.info("Stopped. Happy simming!")


class CommandLine:
    """Parses arguments and dispatches to TrackerApp."""

    def __init__(self, argv: list[str] | None = None) -> None:
        self.argv = argv if argv is not None else sys.argv[1:]
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="simstracker",
            description="Session journal for Sims 4 forever worlds. "
                        "Run with no arguments to open the main window.",
        )
        parser.add_argument("--version", action="version",
                            version=f"%(prog)s {__version__}")
        parser.add_argument("--data-dir", type=Path, default=None,
                            help="override where config and data are stored")

        sub = parser.add_subparsers(dest="command")
        sub.add_parser("home", help="open the main window (default)")
        sub.add_parser("watch", help="run the background watcher")
        sub.add_parser("detect", help="find running Sims processes")
        sub.add_parser("log", help="log a session now")
        sub.add_parser("recap", help="show where you left off")
        sub.add_parser("history", help="browse, search, and export sessions")
        sub.add_parser("sims", help="edit Sims, traits, goals and storylines")

        export = sub.add_parser("export", help="export your journal")
        export.add_argument(
            "--format", default="markdown",
            choices=ExporterRegistry.names(),
            help="output format (default: markdown)",
        )
        export.add_argument("--out", type=Path, default=None,
                            help="write to a file instead of stdout")
        export.add_argument("--sims", action="store_true",
                            help="export the Sim roster instead of sessions")

        sub.add_parser("config", help="show config file location and values")
        return parser

    def run(self) -> int:
        args = self.parser.parse_args(self.argv)
        app = TrackerApp(Config(args.data_dir))
        command = args.command or "home"

        if command == "home":
            app.show_home()
        elif command == "watch":
            app.watch()
        elif command == "detect":
            found = GameWatcher.detect_candidates()
            if found:
                print("Running processes that look like the game:")
                for name in found:
                    print(f"  {name}")
                added = app.config.add_process_names(found)
                print(f"Added to config: {', '.join(added) or 'nothing new'}")
            else:
                print("Nothing found — start the game first, then retry.")
        elif command == "log":
            app.show_log()
        elif command == "recap":
            app.show_recap()
        elif command == "history":
            app.show_history()
        elif command == "sims":
            app.show_sims()
        elif command == "export":
            content = app.export(args.format, args.out, sims=args.sims)
            if not args.out:
                print(content)
        elif command == "config":
            print(f"Config file: {app.config.path}")
            print(f"Database:    {app.config.db_path}")
            print(f"Log file:    {app.config.log_path}")
            print(f"Watching:    {', '.join(app.config.process_names)}")
            print(f"Poll every:  {app.config.poll_seconds}s")
        return 0


def main() -> int:
    try:
        return CommandLine().run()
    except BrokenPipeError:
        # Happens when piping into `head`, `less`, etc. Not an error.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except KeyboardInterrupt:
        return 130
