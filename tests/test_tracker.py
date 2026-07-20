"""Unit tests for the non-UI layers."""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simstracker.config import Config
from simstracker.exporters import ExporterRegistry
from simstracker.models import FieldSpec, Session
from simstracker.repository import SessionRepository
from simstracker.watcher import GameWatcher, SingleInstanceLock

FIELDS = [
    FieldSpec("household", "Household played", prefill_from_last=True),
    FieldSpec("major_events", "Major events", multiline=True),
    FieldSpec("next_time", "Do next time", multiline=True),
]


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestFieldSpec(unittest.TestCase):
    def test_rejects_invalid_key(self):
        with self.assertRaises(ValueError):
            FieldSpec("not a key", "Label")

    def test_round_trips_through_dict(self):
        spec = FieldSpec("household", "Household", multiline=True)
        self.assertEqual(FieldSpec.from_dict(spec.to_dict()), spec)

    def test_derives_label_when_missing(self):
        self.assertEqual(
            FieldSpec.from_dict({"key": "sim_week"}).label, "Sim Week"
        )


class TestSession(unittest.TestCase):
    def test_empty_detection(self):
        self.assertTrue(Session(values={"household": "  "}).is_empty())
        self.assertFalse(Session(values={"household": "Vance"}).is_empty())

    def test_blocks_skip_blank_fields(self):
        session = Session(values={"household": "Vance", "major_events": ""})
        self.assertEqual(session.as_blocks(FIELDS),
                         [("Household played", "Vance")])

    def test_playtime_formatting(self):
        self.assertEqual(Session(played_minutes=95).playtime_text, "1h 35m")
        self.assertEqual(Session(played_minutes=42).playtime_text, "42m")
        self.assertEqual(Session().playtime_text, "")

    def test_summary_truncates_long_text(self):
        session = Session(values={"household": "V" * 80})
        self.assertIn("…", session.summary_line(FIELDS))


class TestRepository(TempDirCase):
    def setUp(self):
        super().setUp()
        self.repo = SessionRepository(self.tmp / "s.db", FIELDS)

    def test_add_and_retrieve(self):
        self.repo.add(Session(values={"household": "Vance",
                                      "major_events": "Buried the cash."}))
        latest = self.repo.latest()
        self.assertEqual(latest.get("household"), "Vance")
        self.assertIn("cash", latest.get("major_events"))
        self.assertEqual(self.repo.count(), 1)

    def test_latest_returns_most_recent(self):
        self.repo.add(Session(values={"household": "First"}))
        self.repo.add(Session(values={"household": "Second"}))
        self.assertEqual(self.repo.latest().get("household"), "Second")

    def test_search_is_case_insensitive(self):
        self.repo.add(Session(values={"major_events": "The Curse broke"}))
        self.repo.add(Session(values={"major_events": "Bakery opened"}))
        self.assertEqual(len(self.repo.search("curse")), 1)
        self.assertEqual(len(self.repo.search("")), 2)

    def test_delete(self):
        session = self.repo.add(Session(values={"household": "Hollow"}))
        self.repo.delete(session.id)
        self.assertEqual(self.repo.count(), 0)

    def test_total_minutes(self):
        self.repo.add(Session(values={"household": "A"}, played_minutes=60))
        self.repo.add(Session(values={"household": "B"}, played_minutes=30))
        self.assertEqual(self.repo.total_minutes(), 90)

    def test_adding_a_field_later_preserves_old_rows(self):
        """Players can add questions to config.json without data loss."""
        self.repo.add(Session(values={"household": "Vance"}))
        extended = FIELDS + [FieldSpec("mood_board", "Mood board")]
        repo2 = SessionRepository(self.tmp / "s.db", extended)
        self.assertEqual(repo2.count(), 1)
        repo2.add(Session(values={"household": "Osei",
                                  "mood_board": "sepia"}))
        self.assertEqual(repo2.latest().get("mood_board"), "sepia")
        self.assertEqual(repo2.all()[-1].get("household"), "Vance")


class TestConfig(TempDirCase):
    def test_creates_file_with_defaults(self):
        config = Config(self.tmp)
        self.assertTrue(config.path.exists())
        self.assertGreater(len(config.fields), 5)
        self.assertIn("ts4_x64.exe", config.process_names)

    def test_round_trip(self):
        config = Config(self.tmp)
        config.poll_seconds = 30
        config.save()
        self.assertEqual(Config(self.tmp).poll_seconds, 30)

    def test_enforces_minimum_poll_interval(self):
        config = Config(self.tmp)
        config.poll_seconds = 0
        config.save()
        self.assertGreaterEqual(Config(self.tmp).poll_seconds, 2)

    def test_corrupt_config_falls_back_to_defaults(self):
        config = Config(self.tmp)
        config.path.write_text("{ not json at all")
        self.assertEqual(Config(self.tmp).poll_seconds, 10)


class TestExporters(TempDirCase):
    def setUp(self):
        super().setUp()
        self.registry = ExporterRegistry(FIELDS)
        self.sessions = [
            Session(values={"household": "Vance",
                            "major_events": "Devon found the cash."},
                    logged_at=dt.datetime(2026, 7, 20, 21, 0),
                    played_minutes=75),
            Session(values={"household": "Hollow",
                            "major_events": "Silas died."},
                    logged_at=dt.datetime(2026, 7, 19, 20, 0)),
        ]

    def test_all_formats_render(self):
        for name in ExporterRegistry.names():
            output = self.registry.get(name).render(self.sessions)
            self.assertIn("Vance", output, f"{name} lost data")

    def test_markdown_is_chronological(self):
        output = self.registry.get("markdown").render(self.sessions)
        self.assertLess(output.index("Silas"), output.index("Devon"))

    def test_table_escapes_pipes_and_newlines(self):
        session = Session(values={"major_events": "a|b\nc"})
        row = self.registry.get("table").render([session])
        self.assertIn("\\|", row)
        self.assertIn("<br>", row)

    def test_json_is_parseable(self):
        import json
        data = json.loads(self.registry.get("json").render(self.sessions))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["household"], "Hollow")

    def test_empty_export_does_not_crash(self):
        for name in ExporterRegistry.names():
            self.assertIsInstance(self.registry.get(name).render([]), str)

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            self.registry.get("papyrus")


class TestWatcher(unittest.TestCase):
    def test_fires_callbacks_on_transitions(self):
        events = []
        watcher = GameWatcher(
            ["fake_game.exe"],
            on_launch=lambda: events.append("launch"),
            on_exit=lambda mins: events.append("exit"),
        )
        running = {"value": False}
        watcher.is_game_running = lambda: running["value"]

        watcher.poll_once()                 # still closed
        running["value"] = True
        watcher.poll_once()                 # launched
        watcher.poll_once()                 # still open, no repeat
        running["value"] = False
        watcher.poll_once()                 # exited
        self.assertEqual(events, ["launch", "exit"])

    def test_prime_suppresses_recap_when_game_already_open(self):
        events = []
        watcher = GameWatcher(["fake.exe"],
                              on_launch=lambda: events.append("launch"))
        watcher.is_game_running = lambda: True
        watcher.prime()
        watcher.poll_once()
        self.assertEqual(events, [])

    def test_reports_session_minutes(self):
        watcher = GameWatcher(["fake.exe"])
        watcher._started_at = dt.datetime.now() - dt.timedelta(minutes=45)
        self.assertGreaterEqual(watcher.session_minutes, 44)

    def test_process_matching_is_case_insensitive(self):
        watcher = GameWatcher(["TS4_x64.exe"])
        self.assertIn("ts4_x64.exe", watcher.process_names)


class TestSingleInstanceLock(TempDirCase):
    def test_second_instance_is_refused(self):
        first = SingleInstanceLock(self.tmp / "t.lock")
        self.assertTrue(first.acquire())
        self.assertFalse(SingleInstanceLock(self.tmp / "t.lock").acquire())
        first.release()
        self.assertTrue(SingleInstanceLock(self.tmp / "t.lock").acquire())

    def test_stale_lock_is_reclaimed(self):
        path = self.tmp / "t.lock"
        path.write_text("999999")  # PID that does not exist
        self.assertTrue(SingleInstanceLock(path).acquire())


if __name__ == "__main__":
    unittest.main(verbosity=2)
