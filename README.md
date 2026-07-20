# 𖢻 Sims Forever Tracker

**A session journal for generational Sims 4 saves.** It notices when The Sims 4
opens and closes, and asks you the right question at the right moment:

- **On launch** → a recap of your last session, so you know exactly where you left off.
- **On exit** → a log form, while you still remember what just happened.

Everything is stored locally in SQLite. No accounts, no cloud, no telemetry.
Export to Markdown, a Notion-ready table, CSV, or JSON whenever you like.

Windows and macOS · Python 3.10+ · MIT licensed

---

## Contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
  - [Customising the questions](#customising-the-questions)
  - [If the game isn't detected](#if-the-game-isnt-detected)
- [Exporting to Notion](#exporting-to-notion)
- [Where your data lives](#where-your-data-lives)
- [Building the executable](#building-the-executable)
- [Automated releases](#automated-releases)
- [Architecture](#architecture)
- [Running the tests](#running-the-tests)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [Related projects](#related-projects)
- [License](#license)

---

## Why this exists

Forever worlds and legacy saves collapse under forgotten details. Who knew about
the affair? Which secrets were at risk? What was Gen 3 supposed to do next?

Notion templates and spreadsheets solve the *storage* problem but not the
*discipline* problem — you have to remember to go and write things down, and by
then you've closed the game and moved on. This tool asks at the only moment you
reliably remember everything: the second you quit.

## Features

| | |
|---|---|
| **Auto-detect** | Watches for the game process and reacts to launch and exit |
| **Recap on launch** | Your last entry, front and centre, before you press play |
| **Log on exit** | A form matching a rotational-play journal, with keyboard shortcuts |
| **Playtime tracking** | Records how long each session ran |
| **Full history** | Browse, search across every field, and delete entries |
| **Four export formats** | Markdown journal, Markdown table, CSV, JSON |
| **Fully customisable** | Rename, add, or remove questions via a JSON config — no code editing |
| **Safe schema upgrades** | Adding a question later never loses existing entries |
| **Game auto-detection** | One button finds your game's executable, whichever renderer you use |
| **Single instance** | A PID lock stops duplicate watchers; launching again opens the main window instead of failing silently |
| **Runs quietly** | No console window in the frozen build; logs to a file for debugging |

## Install

### Option A — download a build (easiest)

Grab `SimsTracker-windows.exe` or `SimsTracker-macos` from the
[Releases](../../releases) page and run it. It sits in the background waiting
for the game. No Python needed.

> **macOS first run:** unsigned binaries are blocked by Gatekeeper. Right-click
> the file → **Open** → **Open** to allow it once, or run
> `xattr -d com.apple.quarantine SimsTracker-macos` in Terminal.

### Option B — run from source

```bash
git clone https://github.com/YOUR-USERNAME/sims-forever-tracker.git
cd sims-forever-tracker
pip install -r requirements.txt
python sims_tracker.py
```

Requires Python 3.10 or newer with Tkinter (bundled with the official
python.org and macOS installers; on Linux, `sudo apt install python3-tk`).
The only third-party dependency is `psutil`.

## Usage

Run with no arguments to open the main window:

```bash
python sims_tracker.py
```

From there, one button starts the background watcher and the rest are one
click away. To go straight to watching (this is what autostart should use):

```bash
python sims_tracker.py watch
```

All commands:

| Command | What it does |
|---|---|
| `sims_tracker.py` or `... home` | Open the main window (default) |
| `... watch` | Run the background watcher |
| `... detect` | Find running Sims processes and add them to your config |
| `... log` | Open the log form now |
| `... recap` | Show where you left off |
| `... history` | Browse, search, export, and delete sessions |
| `... export --format markdown` | Print your journal to the terminal |
| `... export --format table --out journal.md` | Write an export to a file |
| `... config` | Print config, database, and log file locations |
| `... --version` | Version number |
| `... --data-dir PATH` | Use a different data folder (handy for testing) |

Export formats: `markdown`, `table`, `csv`, `json`.

**In the log window:** `Ctrl+S` saves, `Esc` skips, and the household and
sim-week fields prefill from your last entry.

## Configuration

Run `python sims_tracker.py config` to find your `config.json`, then edit it in
any text editor. Changes take effect next time the app starts.

```json
{
  "process_names": ["ts4_x64.exe", "ts4.exe", "the sims 4", "ts4_x64"],
  "poll_seconds": 10,
  "show_recap_on_launch": true,
  "show_log_on_exit": true,
  "theme": "dark",
  "fields": [ ... ]
}
```

| Setting | Meaning |
|---|---|
| `process_names` | Process names that count as "the game is running" |
| `poll_seconds` | How often to check (minimum 2, default 10) |
| `show_recap_on_launch` | Set `false` if you only want the exit prompt |
| `show_log_on_exit` | Set `false` if you only want the launch recap |
| `theme` | `"dark"` or `"light"` |
| `fields` | The questions on the log form (see below) |

### Customising the questions

Each entry in `fields` looks like this:

```json
{
  "key": "secrets_at_risk",
  "label": "Secrets at risk",
  "multiline": true,
  "prefill_from_last": false,
  "help_text": "Who's close to finding out?"
}
```

- `key` — internal name and database column. Letters, digits, and underscores
  only, and don't change it after you've logged entries under it.
- `label` — what you see on the form.
- `multiline` — `true` gives a text box, `false` a single-line field.
- `prefill_from_last` — carries the previous session's answer over.
- `help_text` — optional hint under the label.

Add a new field and the database gains a column automatically on next launch;
existing entries are untouched. Removing a field hides it from the form, but the
old data stays in the database and in exports.

### If the game isn't detected

**Try `detect` first** — with the game running, it finds the executable and
writes it to your config for you:

```bash
python sims_tracker.py detect
```

The same thing is the **Detect my game** button on the main window.

**The most common cause is the renderer.** The Sims 4 ships separate
executables for DirectX 11 (`TS4_x64.exe`) and DirectX 9
(`TS4_DX9_x64.exe`). Which one you get is decided by the EA app's game
settings, or automatically by your GPU — most players have no idea which
they're running. Both are in the defaults now, but if you're on an unusual
build, find yours manually:

- **Windows:** open the game, then Task Manager → **Details** tab → look for the
  Sims process and copy its exact name.
- **macOS:** open the game, then run `ps -A -o comm | grep -i sims` in Terminal
  and use the last path component.

Add it to `process_names` (lowercase) and restart the tracker. Matching is
case-insensitive and also matches names that *start with* an entry, which covers
macOS bundles that append suffixes.

## Exporting to Notion

Two good options:

**A journal page** — narrative, oldest first, with headings per session:

```bash
python sims_tracker.py export --format markdown --out journal.md
```

Open the file, copy everything, and paste into a Notion page. Notion converts
the Markdown headings and bold labels automatically.

**A database table** — one row per session:

```bash
python sims_tracker.py export --format table --out journal.md
```

Paste into Notion and it becomes a table you can then turn into a database
(`/table` → paste). Line breaks inside cells are converted to `<br>` and pipe
characters are escaped so the table never breaks.

You can also export from the **history** window's *Export…* button, which offers
all four formats and a normal save dialog.

## Where your data lives

The app follows each platform's convention rather than writing next to the
executable, so your journal survives reinstalls and app updates:

| Platform | Location |
|---|---|
| Windows | `%APPDATA%\SimsForeverTracker\` |
| macOS | `~/Library/Application Support/SimsForeverTracker/` |
| Linux | `~/.local/share/SimsForeverTracker/` |

Inside you'll find `sessions.db` (your journal), `config.json` (settings),
`tracker.log` (diagnostics), and `tracker.lock` (the single-instance PID file).

**Back up `sessions.db`.** It's a normal SQLite file — copy it anywhere, or open
it with any SQLite browser. This is your save's memory; treat it like the save
itself.

## Building the executable

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name SimsTracker sims_tracker.py
```

The result lands in `dist/` — `SimsTracker.exe` on Windows, `SimsTracker` on
macOS. Use `--windowed` instead of `--noconsole` on macOS if you want a proper
`.app` bundle.

PyInstaller can only build for the platform it runs on — a Windows `.exe` must
be built on Windows. That's what the CI workflow below is for.

## Automated releases

`.github/workflows/build.yml` builds both platforms on GitHub's runners and
attaches the binaries to a Release:

```bash
git tag v1.0.0
git push --tags
```

Wait a few minutes, and `SimsTracker-windows.exe` and `SimsTracker-macos` appear
on your Releases page. The workflow also runs the test suite first and refuses
to build if tests fail. You can trigger it manually from the **Actions** tab
without tagging (`workflow_dispatch`).

## Architecture

Each class has one job, and no layer reaches past its neighbour — the watcher
doesn't know about windows, the windows don't know about SQL.

```
simstracker/
├── models.py      FieldSpec, Session          — plain data, no I/O
├── config.py      Config                      — JSON settings + platform paths
├── repository.py  SessionRepository           — every SQL statement lives here
├── watcher.py     GameWatcher, SingleInstanceLock — process detection
├── exporters.py   Exporter + 4 subclasses     — one class per output format
├── ui.py          BaseWindow → Home/Recap/Log/History — Tkinter
└── app.py         TrackerApp, CommandLine     — wiring and CLI
```

- **`Session` and `FieldSpec`** are value objects. The form, the database
  schema, and all four exports are generated from the same `FieldSpec` list,
  which is why adding a question is a one-line config change.
- **`SessionRepository`** is the only thing that touches SQLite, so swapping
  storage would mean rewriting one file.
- **`GameWatcher`** takes `on_launch` / `on_exit` callbacks rather than opening
  windows itself, which is what makes it testable without a display.
- **`Exporter`** is an abstract base class; each format subclasses it and
  registers with `ExporterRegistry`. Adding a format = adding a class.
- **`BaseWindow`** holds the theming, centering, and always-on-top behaviour
  the four windows share.
- **`HomeWindow`** records the player's choice in `self.action` and closes;
  `TrackerApp` reads it and dispatches. Tk never drives the application.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

35 tests covering models, storage, config, exports, game detection, and the
instance lock. They run headless — no display or game required — because the
watcher is driven through an injected `is_game_running` and the UI layer is
kept separate from the logic.

## Troubleshooting

**Nothing pops up when I open or close the game.**
Run `python sims_tracker.py config` and check the watched process names against
what Task Manager or `ps` actually shows. See
[If the game isn't detected](#if-the-game-isnt-detected).

**The window opens behind the game.**
It pins itself on top for a moment on appearing. If your game is borderless
fullscreen and still covers it, alt-tab once — the window is there. Running the
game in windowed or borderless mode makes this smoother.

**"Another Sims Forever Tracker is already watching."**
You have two copies running, usually because autostart is configured *and* you
started one manually. Close one. If a previous run was force-killed, delete
`tracker.lock` from the data folder.

**Task Manager shows two SimsTracker processes.**
Normal for a one-file build — a small bootloader unpacks the bundle and runs
the real interpreter as a child. It's one app; don't kill either.

**Windows shows a console window.**
You're launching with `python.exe`. Use `pythonw.exe`, or the frozen `.exe`
built with `--noconsole`.

**Antivirus flags the .exe.**
PyInstaller one-file builds are a common false positive because they unpack
themselves at runtime. Building it yourself or running from source avoids it.

**I lost my entries.**
Check the data folder above — the database isn't stored next to the executable,
so moving or replacing the .exe never touches it.

**The recap is blank.**
That's expected before your first logged session. Play, quit, log, and it
appears next launch.

## FAQ

**Does this read my save files?**
No. It only watches whether the game's *process* is running and stores what you
type. It never opens, parses, or modifies anything in your Sims folder — which
also means it can't break your save.

**Does it need mods, or work with them?**
No mods required, and it's mod-agnostic — it works the same whether your save
is vanilla or heavily modded.

**Is it against EA's terms?**
It's an ordinary desktop notes app that checks a process list. It doesn't touch
game files, memory, or network traffic.

**Will it work with The Sims 3 or 2?**
Yes — put that game's process name in `process_names`. Nothing else is
Sims-4-specific.

**Can I use it for other games?**
Also yes. Change `process_names` and rewrite the `fields` list, and it's a
session journal for anything.

**Does it phone home?**
No network code exists in the project at all.

## Contributing

Issues and PRs welcome. If you're adding a feature, please:

1. Keep layers separate — logic in the domain classes, not in the windows
2. Add a test to `tests/test_tracker.py`
3. Run `python -m unittest discover -s tests` before opening the PR

Ideas that would be genuinely useful: a system tray icon, screenshot
attachments per session, a family-tree view, and per-household filtering in the
history window.

## Related projects

Plenty of tools track challenge *points* or family *data*. This one tracks your
*narrative session*, prompted automatically. If you want something different:

- **[SimsChallengeTracker.com](https://www.simschallengetracker.com/)** — web app that tallies legacy challenge points and unlocks
- **SimMattically's Challenge Tracker** — an in-game mod for goal checklists, tied to the household
- **Graveyard** — a desktop GUI for tracking Sims families in detail
- **Sims 4 Save Manager** — backup and restore for save files, with notes
- Notion templates and save-file spreadsheets from the simblr community

## License

MIT — see [LICENSE](LICENSE). Do what you like; credit appreciated.

Not affiliated with, endorsed by, or connected to Electronic Arts or Maxis.
"The Sims" is a trademark of Electronic Arts, Inc.