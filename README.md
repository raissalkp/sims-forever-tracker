# 𖢻 Sims Forever Tracker

**A session journal for generational Sims 4 saves.** It notices when The Sims 4
opens and closes, and asks you the right question at the right moment:

- **On launch** → a recap of your last session, so you know exactly where you left off.
- **On exit** → a log form, while you still remember what just happened.

Everything is stored locally in SQLite. No accounts, no cloud, no telemetry.
Export to Markdown, a Notion-ready table, CSV, or JSON whenever you like.

Windows and macOS · Python 3.10+ · MIT licensed

[![Latest release](https://img.shields.io/github/v/release/raissalkp/sims-forever-tracker?label=download&color=7fc241)](../../releases/latest)
[![Downloads](https://img.shields.io/github/downloads/raissalkp/sims-forever-tracker/total?color=7fc241)](../../releases)
[![Build](https://img.shields.io/github/actions/workflow/status/raissalkp/sims-forever-tracker/release.yml)](../../actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
---

## Contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [Install](#install)
- [Usage](#usage)
- [Start automatically at login](#start-automatically-at-login)
  - [Windows](#windows-task-scheduler)
  - [macOS](#macos-launchd)
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
| **Story bible** | A Sims & households page: traits, aspirations, careers, goals, storylines, secrets, and relationships, grouped by family and generation |
| **Game auto-detection** | One button finds your game's executable, whichever renderer you use |
| **Single instance** | A PID lock stops duplicate watchers; launching again opens the main window instead of failing silently |
| **Runs quietly** | No console window in the frozen build; logs to a file for debugging |

## Install

### Option A — download a build (easiest)

**⬇️ [Download for Windows](../../releases/latest/download/SimsTracker.exe)**
· **⬇️ [Download for macOS](../../releases/latest/download/SimsTracker-macos.zip)**

Those links always point at the newest release — no need to browse the
Releases page or dig through build artifacts. No Python needed.

Older versions live on the [Releases](../../releases) page.

### Skip the macOS warning entirely (optional)

Installing with `curl` avoids Gatekeeper's "Apple could not verify…" prompt,
because the quarantine flag is set by web browsers rather than by macOS
itself — files fetched with `curl` never get it. This is the same mechanism
Homebrew relies on.

```bash
curl -fsSL https://raw.githubusercontent.com/raissalkp/sims-forever-tracker/main/install.sh | bash
```

It downloads the latest release, installs `SimsTracker.app` to
`/Applications`, and leaves your saved sessions untouched. Read
[`install.sh`](install.sh) first if you like — you should with any install
script, including this one.

### First run

The app isn't code-signed — that needs a paid developer account from Apple
and a certificate from Microsoft, which isn't worth it for a free tool. Both
systems will warn you once. This is a one-time step.

**macOS**

1. Unzip and drag **SimsTracker.app** to your Applications folder.
2. Double-click it. You'll get *"Apple could not verify… is free of
   malware."* Click **Done**.
3. Open **System Settings → Privacy & Security**, scroll down to *"SimsTracker
   was blocked to protect your Mac"*, and click **Open Anyway**.
4. Launch it again and choose **Open**. It'll run normally from then on.

The old right-click → Open trick no longer works on current macOS versions.

If you'd rather do it in one step:

```bash
xattr -dr com.apple.quarantine /Applications/SimsTracker.app
```

The `-r` is required — an app bundle is a folder, and every file inside it is
quarantined.

**Windows**

Double-click the `.exe`. SmartScreen shows *"Windows protected your PC"* —
click **More info**, then **Run anyway**.

Some antivirus tools also flag one-file PyInstaller builds, because they
unpack themselves to a temp folder at startup. It's a well-known false
positive. Build it yourself or run from source if you'd rather not take my
word for it.



### Option B — run from source

```bash
git clone https://github.com/raissalkp/sims-forever-tracker.git
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
| `... sims` | Edit Sims, traits, aspirations, goals, and storylines |
| `... history` | Browse, search, export, and delete sessions |
| `... export --format markdown` | Print your journal to the terminal |
| `... export --sims --format table` | Export the Sim roster instead of sessions |
| `... export --format table --out journal.md` | Write an export to a file |
| `... config` | Print config, database, and log file locations |
| `... --version` | Version number |
| `... --data-dir PATH` | Use a different data folder (handy for testing) |

Export formats: `markdown`, `table`, `csv`, `json`.

**Keyboard:** `Tab` and `Shift+Tab` move between fields (including out of
multi-line boxes) and the form scrolls to follow, so long forms don't need
the mouse at all. `Ctrl+S` saves, `Esc` closes. In the log window, the
household and sim-week fields prefill from your last entry.

## Start automatically at login

### Windows (Task Scheduler)

1. Press <kbd>Win</kbd> and open **Task Scheduler**
2. **Create Basic Task…** → name it `Sims Forever Tracker`
3. Trigger: **When I log on**
4. Action: **Start a program**
   - *If using the .exe:* Program = the full path to `SimsTracker-windows.exe`, Arguments = `watch`
   - *If using source:* Program = `pythonw.exe` (the **w** matters — no console
     window), Arguments = the full path to `sims_tracker.py`, Start in = the
     project folder
5. Finish. Optionally reopen the task's properties and untick
   *"Stop the task if it runs longer than…"* under **Settings**, so it isn't
   killed after 3 days.

### macOS (launchd)

Save the following as `~/Library/LaunchAgents/com.simstracker.plist`, adjusting
the path to wherever you put the binary or script:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.simstracker</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Applications/SimsTracker.app/Contents/MacOS/SimsTracker</string>
    <string>watch</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

Running from source instead? Use two `<string>` entries: the output of
`which python3`, then the full path to `sims_tracker.py`.

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.simstracker.plist
```

To stop it later: `launchctl unload ~/Library/LaunchAgents/com.simstracker.plist`

## Sims & households

The **Sims & households** page is a story bible for generational saves. One
profile per Sim, grouped by family and generation:

- Name, household, generation, and role in the story
- Life stage or status (including deceased and ghost)
- **Traits, aspiration, and career**
- Goals for the generation, and their storyline arc
- Secrets they hold, and key relationships
- Free-form notes

It exports in all four formats, so a Notion story-bible page is one command:

```bash
python sims_tracker.py export --sims --format markdown --out roster.md
```

The fields are configurable exactly like the session log — see `sim_fields`
in `config.json`. Add a question, and the database gains a column on next
launch without touching your existing profiles.

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
| `config_version` | Set by the app. Lets an update merge in new defaults once, without overwriting your edits. Don't change it by hand |
| `fields` | The questions on the session log form (see below) |
| `sim_fields` | The questions on a Sim profile — same format as `fields` |

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

### Upgrading to a new release

**Downloading a new version never resets anything.** Because the data folder
is separate from the executable, you replace `SimsTracker.exe` and everything
carries over:

- Every logged session and every Sim profile is kept
- New fields added by an update appear as new columns; existing entries are
  untouched
- Your `config.json` keeps your own settings, custom fields, and process
  names — and *gains* any new defaults the update introduced (a newly
  supported game executable, a new profile field). Check `tracker.log` after
  the first launch; it lists exactly what the upgrade added.

Nothing is stored inside the binary, so you can delete and re-download it as
often as you like.

**Back up `sessions.db`.** It's a normal SQLite file — copy it anywhere, or open
it with any SQLite browser. This is your save's memory; treat it like the save
itself.

## Building the executable

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole \
            --collect-submodules simstracker \
            --icon assets/icon.ico \
            --add-data "assets/icon.png:assets" \
            --name SimsTracker sims_tracker.py
```

On Windows, `--add-data` needs a semicolon instead of a colon:
`"assets\icon.png;assets"`. The included `build.ps1` handles this, along with
stopping any running tracker and clearing PyInstaller's cache.

**Windows metadata:** `version_info.txt` embeds the product name, version,
description, and copyright into the `.exe`, so Explorer and the Properties →
Details tab show proper app information instead of just a filename. Keep its
version numbers in step with `__version__` in `simstracker/app.py` — there's a
test that checks this.

**Icons:** `assets/icon.ico` is used for the Windows executable,
`assets/icon.icns` for macOS, and `assets/icon.png` is bundled so the app can
show the logo in its own title bar and taskbar entry.

The result lands in `dist/`. On Windows that's `SimsTracker.exe`.

On macOS use `--windowed` instead of `--noconsole`, which produces **two**
things: `dist/SimsTracker` (a raw Unix executable that only runs from a
terminal — Finder opens it in a text editor) and `dist/SimsTracker.app` (the
double-clickable bundle). **Ship the `.app`.**

A `.app` is a directory, so archive it with `ditto` rather than `zip` — it
preserves the bundle structure and the executable bit:

```bash
ditto -c -k --sequesterRsrc --keepParent dist/SimsTracker.app SimsTracker-macos.zip
```

PyInstaller can only build for the platform it runs on — a Windows `.exe` must
be built on Windows. That's what the CI workflow below is for.

## Automated releases

`.github/workflows/release.yml` runs the tests, then builds both platforms on
GitHub's runners and attaches the binaries to a Release:

```bash
git tag v1.0.0
git push --tags
```

Wait a few minutes, and `SimsTracker.exe` and `SimsTracker-macos.zip`
appear on your Releases page.

**One-time repo setting:** Settings → Actions → General → Workflow permissions
→ **Read and write permissions**. Without it the release step fails with a 403,
because the repo default overrides the workflow's declared permissions.

### Permanent download links

Because the workflow attaches assets with fixed filenames, GitHub exposes a
URL that always resolves to the newest release:

```
https://github.com/USER/REPO/releases/latest/download/SimsTracker-windows.exe
```

That's what the download links at the top of this README use, in the
repo-relative form `../../releases/latest/download/<filename>`. Nothing needs
updating when you cut a new version — as long as the asset filenames stay the
same, the links keep working forever.

This is different from build **artifacts**, which the Actions tab produces on
every run: those expire after 90 days, require a GitHub login to download, and
arrive as zip files. Release assets are permanent, public, and downloaded
directly. Only tagged builds create them. The workflow also runs the test suite first and refuses
to build if tests fail. You can trigger it manually from the **Actions** tab
without tagging (`workflow_dispatch`).

## Architecture

Each class has one job, and no layer reaches past its neighbour — the watcher
doesn't know about windows, the windows don't know about SQL.

```
simstracker/
├── models.py      FieldSpec, ValueBag → Session / SimProfile — no I/O
├── config.py      Config                      — JSON settings + platform paths
├── repository.py  TableRepository → Session/SimRepository — all the SQL
├── watcher.py     GameWatcher, SingleInstanceLock — process detection
├── exporters.py   Exporter + 4 subclasses     — one class per output format
├── ui.py          BaseWindow → Home/Recap/Log/History/Sims, FieldForm
└── app.py         TrackerApp, CommandLine     — wiring and CLI
```

- **`FieldSpec` and `ValueBag`** are the core abstraction. A session and a
  Sim profile are both "a list of configurable questions with free-text
  answers", so they share a mixin — and the form builder, the schema
  migration, and all four exporters work on either without modification.
  Adding a question anywhere is a one-line config change.
- **`TableRepository`** is an abstract base holding the connection, the
  schema migration, and the generic queries. `SessionRepository` and
  `SimRepository` supply only their table name and row mapping. All the SQL
  in the app lives in this one file.
- **`FieldForm`** builds and reads a form from a `FieldSpec` list, shared by
  the session log and the Sim editor.
- **`GameWatcher`** takes `on_launch` / `on_exit` callbacks rather than opening
  windows itself, which is what makes it testable without a display.
- **`Exporter`** is an abstract base class; each format subclasses it and
  registers with `ExporterRegistry`. Adding a format = adding a class.
- **`BaseWindow`** holds the theming, centering, and always-on-top behaviour
  every window shares.
- **`HomeWindow`** records the player's choice in `self.action` and closes;
  `TrackerApp` reads it and dispatches. Tk never drives the application.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

63 tests covering models, storage, config upgrades, exports, the Sim roster,
game detection, and the instance lock. They run headless — no display or game required — because the
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

**On macOS the download opens as pages of garbled text.**
You're launching the raw Unix executable instead of the app bundle. Finder
can't run those, so it opens them in a text editor. Download
`SimsTracker-macos.zip` from Releases, unzip it, and use the **SimsTracker.app**
inside. (Releases before v1.3.1 shipped the raw binary by mistake — it works,
but only from Terminal.)

**Two-finger / trackpad scrolling does nothing on macOS.**
Fixed in v1.3.4. Scroll events carry different values on each platform —
macOS sends small ones that the old handler rounded down to zero. Keyboard
navigation works too: Tab moves between fields and the form scrolls to
follow.

**A button label looks cut off.**
Fixed in v1.3.2 — the main window's buttons are on a grid that shares the
width evenly instead of running off the edge. If you're on an older build,
resizing the window wider brings the full label back.

**Task Manager shows two SimsTracker processes.**
Normal for a one-file build — a small bootloader unpacks the bundle and runs
the real interpreter as a child. It's one app; don't kill either.

**Windows shows a console window.**
You're launching with `python.exe`. Use `pythonw.exe`, or the frozen `.exe`
built with `--noconsole`.

**Antivirus flags the .exe.**
PyInstaller one-file builds are a common false positive because they unpack
themselves at runtime. Building it yourself or running from source avoids it.

**I updated and something's missing.**
Nothing is stored in the executable, so an update can't remove data. Check
`tracker.log` — the first line after an upgrade lists what changed. If a field
you added yourself has vanished from the form, check that it's still in
`sim_fields` or `fields` in `config.json`; the data is still in the database
either way.

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

## Code signing

The releases are unsigned, which is why both systems warn on first launch.
Signing properly means:

- **macOS** — an Apple Developer Program membership ($99/year), a Developer ID
  certificate, and notarisation through Apple's service. Fully automatable in
  the release workflow with the certificate held in repo secrets.
- **Windows** — a code-signing certificate from a commercial CA (roughly
  $200–400/year). SmartScreen also builds reputation over time, so warnings
  fade as more people download a given signed binary.

Neither is worth it for a free hobby tool, so the warnings are documented
instead. If this ever gets enough users to justify it, the workflow is the
only thing that needs changing.

## License

MIT — see [LICENSE](LICENSE). Do what you like; credit appreciated.

Not affiliated with, endorsed by, or connected to Electronic Arts or Maxis.
"The Sims" is a trademark of Electronic Arts, Inc.
