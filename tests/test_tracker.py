"""Unit tests for the non-UI layers."""

import datetime as dt
import os
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simstracker.config import Config
from simstracker.exporters import ExporterRegistry
from simstracker.models import FieldSpec, Session, SimProfile
from simstracker.repository import SessionRepository, SimRepository
from simstracker.resources import Assets
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


class TestConfigUpgrade(TempDirCase):
    """A new release must give existing installs the new defaults."""

    def _write_old_config(self, **overrides) -> None:
        import json
        config = Config(self.tmp)
        raw = json.loads(config.path.read_text())
        raw["config_version"] = 1
        raw.update(overrides)
        config.path.write_text(json.dumps(raw))

    def test_new_process_names_reach_existing_installs(self):
        self._write_old_config(process_names=["ts4_x64.exe"])
        upgraded = Config(self.tmp)
        self.assertIn("ts4_dx9_x64.exe", upgraded.process_names)

    def test_new_sim_fields_reach_existing_installs(self):
        config = Config(self.tmp)
        import json
        raw = json.loads(config.path.read_text())
        raw["config_version"] = 1
        raw["sim_fields"] = [f for f in raw["sim_fields"]
                             if f["key"] != "storyline"]
        config.path.write_text(json.dumps(raw))
        self.assertIn("storyline", [f.key for f in Config(self.tmp).sim_fields])

    def test_player_customisations_survive_the_merge(self):
        import json
        config = Config(self.tmp)
        raw = json.loads(config.path.read_text())
        raw["config_version"] = 1
        raw["process_names"] = ["my_custom_game.exe"]
        raw["sim_fields"].append({"key": "theme_song", "label": "Theme song"})
        raw["poll_seconds"] = 42
        config.path.write_text(json.dumps(raw))

        upgraded = Config(self.tmp)
        self.assertIn("my_custom_game.exe", upgraded.process_names)
        self.assertIn("theme_song", [f.key for f in upgraded.sim_fields])
        self.assertEqual(upgraded.poll_seconds, 42)

    def test_merge_runs_once_not_every_launch(self):
        self._write_old_config(process_names=["ts4_x64.exe"])
        Config(self.tmp)                       # performs the upgrade
        second = Config(self.tmp)              # already current
        self.assertEqual(second.upgrade_notes, [])
        self.assertEqual(second.process_names.count("ts4_dx9_x64.exe"), 1)

    def test_upgrade_notes_describe_what_changed(self):
        self._write_old_config(process_names=["ts4_x64.exe"])
        notes = Config(self.tmp).upgrade_notes
        self.assertTrue(any("ts4_dx9" in n for n in notes), notes)


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
    MARKER = "python"   # matches the test runner, as the app matches itself

    def _lock(self, marker: str | None = None) -> SingleInstanceLock:
        return SingleInstanceLock(self.tmp / "t.lock",
                                  marker=marker or self.MARKER)

    def test_second_instance_is_refused(self):
        first = self._lock()
        self.assertTrue(first.acquire())
        self.assertFalse(self._lock().acquire())
        first.release()
        self.assertTrue(self._lock().acquire())

    def test_stale_lock_is_reclaimed(self):
        (self.tmp / "t.lock").write_text("999999")  # PID that cannot exist
        self.assertTrue(self._lock().acquire())

    def test_unrelated_process_does_not_hold_the_lock(self):
        """PID reuse must not lock the player out permanently."""
        (self.tmp / "t.lock").write_text(str(os.getpid()))
        self.assertTrue(self._lock(marker="definitely-not-this-app").acquire())

    def test_marker_matching_ignores_punctuation(self):
        """SimsTracker.exe and sims_tracker.py must both be recognised."""
        norm = SingleInstanceLock._normalise
        self.assertEqual(norm("SimsTracker.exe"), "simstrackerexe")
        self.assertIn(norm("simstracker"), norm("sims_tracker.py"))

    def test_holder_pid_is_reported(self):
        first = self._lock()
        first.acquire()
        second = self._lock()
        second.acquire()
        self.assertEqual(second.holder_pid, os.getpid())
        first.release()


class TestDetectCandidates(unittest.TestCase):
    def test_finds_matching_processes_and_excludes_self(self):
        class FakeProc:
            def __init__(self, name):
                self.info = {"name": name}

        import simstracker.watcher as w
        original = w.psutil.process_iter
        w.psutil.process_iter = lambda attrs=None: [
            FakeProc("TS4_DX9_x64.exe"),
            FakeProc("TS4_x64.exe"),
            FakeProc("SimsTracker.exe"),     # our own app, must be skipped
            FakeProc("chrome.exe"),
        ]
        try:
            found = GameWatcher.detect_candidates()
        finally:
            w.psutil.process_iter = original
        self.assertIn("ts4_dx9_x64.exe", found)
        self.assertIn("ts4_x64.exe", found)
        self.assertNotIn("simstracker.exe", found)
        self.assertNotIn("chrome.exe", found)


class TestConfigProcessNames(TempDirCase):
    def test_add_process_names_deduplicates(self):
        config = Config(self.tmp)
        added = config.add_process_names(["TS4_Weird_Build.exe", "ts4_x64.exe"])
        self.assertEqual(added, ["ts4_weird_build.exe"])  # 2nd already default
        self.assertIn("ts4_weird_build.exe", Config(self.tmp).process_names)

    def test_dx9_is_a_default(self):
        self.assertIn("ts4_dx9_x64.exe", Config(self.tmp).process_names)


SIM_FIELDS = [
    FieldSpec("name", "Sim name"),
    FieldSpec("household", "Household / family"),
    FieldSpec("generation", "Generation"),
    FieldSpec("story_role", "Role in the story"),
    FieldSpec("traits", "Traits", multiline=True),
    FieldSpec("aspiration", "Aspiration"),
    FieldSpec("goals", "Goals", multiline=True),
]


class TestSimProfile(unittest.TestCase):
    def test_display_name_falls_back(self):
        self.assertEqual(SimProfile().display_name, "(unnamed Sim)")
        self.assertEqual(
            SimProfile(values={"name": "Marisol Vance"}).display_name,
            "Marisol Vance")

    def test_household_falls_back(self):
        self.assertEqual(SimProfile().household, "No household")

    def test_summary_includes_context(self):
        sim = SimProfile(values={"name": "Colm Brennan",
                                 "generation": "Gen 1",
                                 "story_role": "The Thief"})
        line = sim.summary_line()
        self.assertIn("Colm Brennan", line)
        self.assertIn("Gen 1", line)

    def test_markdown_does_not_repeat_the_name(self):
        sim = SimProfile(values={"name": "Ama Osei", "traits": "Hot-Headed"})
        md = sim.to_markdown(SIM_FIELDS)
        self.assertIn("## Ama Osei", md)
        self.assertEqual(md.count("Ama Osei"), 1)
        self.assertIn("Hot-Headed", md)


class TestSimRepository(TempDirCase):
    def setUp(self):
        super().setUp()
        self.repo = SimRepository(self.tmp / "s.db", SIM_FIELDS)

    def test_add_and_retrieve(self):
        self.repo.add(SimProfile(values={"name": "Silas Hollow",
                                         "household": "Hollow",
                                         "traits": "Evil, Self-Assured"}))
        sim = self.repo.latest()
        self.assertEqual(sim.display_name, "Silas Hollow")
        self.assertIn("Evil", sim.get("traits"))

    def test_update_changes_not_duplicates(self):
        sim = self.repo.add(SimProfile(values={"name": "Kira", "goals": "a"}))
        sim.values["goals"] = "b"
        self.repo.update(sim)
        self.assertEqual(self.repo.count(), 1)
        self.assertEqual(self.repo.get_by_id(sim.id).get("goals"), "b")

    def test_update_without_id_inserts(self):
        self.repo.update(SimProfile(values={"name": "New Sim"}))
        self.assertEqual(self.repo.count(), 1)

    def test_grouped_by_household_then_generation(self):
        for name, house, gen in [("Ash", "Vance", "Gen 4"),
                                 ("Marisol", "Vance", "Gen 1"),
                                 ("Ama", "Osei", "Gen 1")]:
            self.repo.add(SimProfile(values={"name": name,
                                             "household": house,
                                             "generation": gen}))
        order = [s.display_name for s in self.repo.all()]
        self.assertEqual(order, ["Ama", "Marisol", "Ash"])

    def test_households_are_listed_once(self):
        self.repo.add(SimProfile(values={"name": "A", "household": "Vance"}))
        self.repo.add(SimProfile(values={"name": "B", "household": "Vance"}))
        self.assertEqual(self.repo.households(), ["Vance"])

    def test_search_across_fields(self):
        self.repo.add(SimProfile(values={"name": "Colm",
                                         "traits": "Kleptomaniac"}))
        self.repo.add(SimProfile(values={"name": "Ama",
                                         "traits": "Hot-Headed"}))
        self.assertEqual(len(self.repo.search("klepto")), 1)

    def test_sims_and_sessions_share_a_database(self):
        """Both tables must coexist in the one file without clashing."""
        sessions = SessionRepository(self.tmp / "s.db", FIELDS)
        sessions.add(Session(values={"household": "Vance"}))
        self.repo.add(SimProfile(values={"name": "Marisol"}))
        self.assertEqual(sessions.count(), 1)
        self.assertEqual(self.repo.count(), 1)

    def test_adding_a_sim_field_later_preserves_rows(self):
        self.repo.add(SimProfile(values={"name": "Vera"}))
        extended = SIM_FIELDS + [FieldSpec("theme_song", "Theme song")]
        repo2 = SimRepository(self.tmp / "s.db", extended)
        self.assertEqual(repo2.count(), 1)
        repo2.add(SimProfile(values={"name": "Damon",
                                     "theme_song": "something occult"}))
        self.assertEqual(repo2.search("occult")[0].display_name, "Damon")


class TestRosterExport(unittest.TestCase):
    def setUp(self):
        self.registry = ExporterRegistry(SIM_FIELDS)
        self.sims = [
            SimProfile(values={"name": "Marisol Vance", "household": "Vance",
                               "traits": "Ambitious, Creative, Paranoid"}),
            SimProfile(values={"name": "Colm Brennan", "household": "Brennan",
                               "traits": "Kleptomaniac"}),
        ]

    def test_every_format_handles_sims(self):
        for name in ExporterRegistry.names():
            output = self.registry.get(name).render(self.sims)
            self.assertIn("Marisol Vance", output, f"{name} lost data")
            self.assertIn("Kleptomaniac", output, f"{name} lost data")

    def test_roster_has_no_date_column(self):
        table = self.registry.get("table").render(self.sims)
        self.assertNotIn("| Date |", table)

    def test_roster_keeps_household_order(self):
        md = self.registry.get("markdown").render(self.sims)
        self.assertLess(md.index("Marisol"), md.index("Colm"))
        self.assertIn("Sim roster", md)


class TestConfigSimFields(TempDirCase):
    def test_sim_fields_have_sensible_defaults(self):
        keys = [f.key for f in Config(self.tmp).sim_fields]
        for expected in ("name", "household", "traits", "aspiration",
                         "goals", "storyline"):
            self.assertIn(expected, keys)

    def test_sim_fields_round_trip(self):
        config = Config(self.tmp)
        config._sim_field_data.append({"key": "theme_song",
                                       "label": "Theme song"})
        config.save()
        self.assertIn("theme_song",
                      [f.key for f in Config(self.tmp).sim_fields])


class TestAssets(unittest.TestCase):
    def test_icon_files_ship_with_the_repo(self):
        for name in ("icon.png", "icon.ico", "icon.icns"):
            self.assertIsNotNone(Assets.path(name), f"{name} is missing")

    def test_missing_asset_returns_none_rather_than_raising(self):
        self.assertIsNone(Assets.path("no-such-file.png"))


class TestPackagingFiles(unittest.TestCase):
    """The build breaks in confusing ways if these go missing."""

    ROOT = pathlib.Path(__file__).resolve().parent.parent

    def test_required_files_exist(self):
        for name in ("requirements.txt", "sims_tracker.py", "README.md",
                     "LICENSE", ".github/workflows/release.yml"):
            self.assertTrue((self.ROOT / name).exists(), f"{name} is missing")

    def test_requirements_lists_psutil(self):
        text = (self.ROOT / "requirements.txt").read_text().lower()
        self.assertIn("psutil", text)


class TestVersionSanity(unittest.TestCase):
    """Cheap guard against source and tests drifting out of sync.

    The CI failure that motivated this happened because some files were
    updated in the repo and others weren't. This won't catch every case,
    but it fails loudly if the package can't expose a coherent version.
    """

    def test_version_is_importable_and_sane(self):
        import simstracker
        parts = simstracker.__version__.split(".")
        self.assertEqual(len(parts), 3, simstracker.__version__)
        self.assertTrue(all(p.isdigit() for p in parts))

    def test_sim_features_are_present(self):
        """Fails fast if only some v1.2 files were copied over."""
        from simstracker.models import SimProfile          # noqa: F401
        from simstracker.repository import SimRepository   # noqa: F401
        from simstracker.ui import SimsWindow              # noqa: F401
        from simstracker.config import Config
        self.assertTrue(hasattr(Config, "sim_fields"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
