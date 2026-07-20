"""Tkinter windows.

BaseWindow handles everything the three real windows share: theming,
sizing, centering, and the brief always-on-top nudge that gets the window
noticed when it appears over the game's exit screen.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable
from .models import FieldSpec, Session
from .repository import SessionRepository

THEMES = {
    "dark": {
        "bg": "#1e2128", "surface": "#272b34", "text": "#e8e9ed",
        "muted": "#9aa0ad", "accent": "#7fc241", "entry_bg": "#161920",
    },
    "light": {
        "bg": "#f5f6f8", "surface": "#ffffff", "text": "#1e2128",
        "muted": "#6b7280", "accent": "#4c8b1f", "entry_bg": "#ffffff",
    },
}


class BaseWindow:
    """Shared setup for every window in the app."""

    title_text = "Sims Forever Tracker"
    width = 660
    height = 740

    def __init__(self, theme: str = "dark") -> None:
        self.palette = THEMES.get(theme, THEMES["dark"])
        self.root = tk.Tk()
        self.root.title(self.title_text)
        self.root.configure(bg=self.palette["bg"])
        self._center()
        self._apply_style()
        self._nudge_to_front()
        self.root.bind("<Escape>", lambda _e: self.close())
        self.body = ttk.Frame(self.root, padding=18, style="App.TFrame")
        self.body.pack(fill="both", expand=True)
        self.build()

    # hooks

    def build(self) -> None:
        """Subclasses construct their widgets here."""

    def show(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # chrome

    def _center(self) -> None:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - self.width) // 2)
        y = max(0, (screen_h - self.height) // 3)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.minsize(480, 400)

    def _nudge_to_front(self) -> None:
        """Briefly pin on top so the window isn't lost behind the game."""
        self.root.attributes("-topmost", True)
        self.root.after(
            1200, lambda: self.root.attributes("-topmost", False)
        )
        self.root.lift()
        self.root.focus_force()

    def _apply_style(self) -> None:
        p = self.palette
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=p["bg"])
        style.configure("Card.TFrame", background=p["surface"])
        style.configure("TLabel", background=p["bg"], foreground=p["text"])
        style.configure("Muted.TLabel", background=p["bg"],
                        foreground=p["muted"])
        style.configure("Heading.TLabel", background=p["bg"],
                        foreground=p["text"],
                        font=("TkDefaultFont", 15, "bold"))
        style.configure("Field.TLabel", background=p["bg"],
                        foreground=p["text"],
                        font=("TkDefaultFont", 10, "bold"))
        style.configure("TButton", padding=8)
        style.configure("Accent.TButton", padding=8)
        style.map("Accent.TButton",
                  background=[("!disabled", p["accent"])],
                  foreground=[("!disabled", "#10130f")])
        style.configure("TEntry", fieldbackground=p["entry_bg"],
                        foreground=p["text"], insertcolor=p["text"])

    def _make_text(self, parent: tk.Misc, height: int = 3,
                   readonly: bool = False) -> tk.Text:
        p = self.palette
        widget = tk.Text(
            parent, height=height, wrap="word", relief="flat",
            bg=p["entry_bg"] if not readonly else p["surface"],
            fg=p["text"], insertbackground=p["text"],
            padx=10, pady=8, borderwidth=0,
            font=("TkDefaultFont", 10),
        )
        widget.tag_configure(
            "heading", foreground=p["accent"],
            font=("TkDefaultFont", 11, "bold"), spacing1=8, spacing3=2,
        )
        widget.tag_configure("muted", foreground=p["muted"])
        return widget


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container with a working mouse wheel."""

    def __init__(self, parent: tk.Misc, bg: str) -> None:
        super().__init__(parent, style="App.TFrame")
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="App.TFrame")

        self._window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inner.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._window, width=e.width),
        )
        self._bind_wheel()

    def _bind_wheel(self) -> None:
        def on_wheel(event: tk.Event) -> None:
            delta = event.delta
            if delta == 0:                       # X11 sends Button-4/5
                delta = 120 if getattr(event, "num", 5) == 4 else -120
            self.canvas.yview_scroll(int(-delta / 120), "units")

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, on_wheel)


class RecapWindow(BaseWindow):
    """Shown on game launch: where did I leave off?"""

    title_text = "Previously, in your forever world…"
    height = 620

    def __init__(self, session: Session | None, fields: list[FieldSpec],
                 theme: str = "dark", stats: str = "") -> None:
        self.session = session
        self.fields = fields
        self.stats = stats
        super().__init__(theme)

    def build(self) -> None:
        if self.session is None:
            ttk.Label(
                self.body,
                text="No sessions logged yet.\n\nGo play — I'll ask what "
                     "happened when you quit.\nHave fun!",
                style="TLabel", justify="center",
                font=("TkDefaultFont", 12),
            ).pack(expand=True)
        else:
            ttk.Label(self.body, text="Last session",
                      style="Heading.TLabel").pack(anchor="w")
            subtitle = f"{self.session.logged_at:%A %d %B, %H:%M}"
            if self.session.playtime_text:
                subtitle += f"  ·  played {self.session.playtime_text}"
            ttk.Label(self.body, text=subtitle,
                      style="Muted.TLabel").pack(anchor="w", pady=(2, 12))

            text = self._make_text(self.body, height=24, readonly=True)
            text.pack(fill="both", expand=True)
            for label, value in self.session.as_blocks(self.fields):
                text.insert("end", f"{label}\n", ("heading",))
                text.insert("end", f"{value}\n\n")
            text.configure(state="disabled")

        if self.stats:
            ttk.Label(self.body, text=self.stats,
                      style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

        ttk.Button(self.body, text="Got it — have fun!",
                   style="Accent.TButton",
                   command=self.close).pack(pady=(14, 0))


class LogWindow(BaseWindow):
    """Shown on game exit: log what happened."""

    title_text = "What happened this session?"

    def __init__(self, fields: list[FieldSpec], repository: SessionRepository,
                 played_minutes: int | None = None, theme: str = "dark",
                 on_saved: Callable[[Session], None] | None = None) -> None:
        self.fields = fields
        self.repository = repository
        self.played_minutes = played_minutes
        self.on_saved = on_saved
        self.widgets: dict[str, tk.Widget] = {}
        self.saved_session: Session | None = None
        super().__init__(theme)

    def build(self) -> None:
        header = ttk.Frame(self.body, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Session log",
                  style="Heading.TLabel").pack(anchor="w")
        subtitle = "Fill in what you remember — blank fields are skipped."
        if self.played_minutes:
            hours, minutes = divmod(self.played_minutes, 60)
            played = f"{hours}h {minutes}m" if hours else f"{minutes}m"
            subtitle = f"You played for {played}.  " + subtitle
        ttk.Label(header, text=subtitle,
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 6))

        scroller = ScrollableFrame(self.body, bg=self.palette["bg"])
        scroller.pack(fill="both", expand=True)
        form = scroller.inner

        previous = self.repository.latest()
        for spec in self.fields:
            ttk.Label(form, text=spec.label,
                      style="Field.TLabel").pack(anchor="w", pady=(10, 2))
            if spec.help_text:
                ttk.Label(form, text=spec.help_text,
                          style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
            if spec.multiline:
                widget: tk.Widget = self._make_text(form, height=3)
                widget.pack(fill="x", padx=(0, 4))
            else:
                widget = ttk.Entry(form)
                widget.pack(fill="x", padx=(0, 4), ipady=4)
                if spec.prefill_from_last and previous:
                    widget.insert(0, previous.get(spec.key))
            self.widgets[spec.key] = widget

        footer = ttk.Frame(self.body, style="App.TFrame")
        footer.pack(fill="x", pady=(14, 0))
        ttk.Button(footer, text="Save session", style="Accent.TButton",
                   command=self.save).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Skip",
                   command=self.close).pack(side="right")
        ttk.Label(footer, text="Ctrl+S to save · Esc to skip",
                  style="Muted.TLabel").pack(side="left")

        self.root.bind("<Control-s>", lambda _e: self.save())
        self.root.bind("<Control-Return>", lambda _e: self.save())
        # Focus the first field so the player can start typing immediately.
        if self.fields:
            self.widgets[self.fields[0].key].focus_set()

    def collect(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                values[key] = widget.get("1.0", "end").strip()
            else:
                values[key] = widget.get().strip()
        return values

    def save(self) -> None:
        session = Session(values=self.collect(),
                          played_minutes=self.played_minutes)
        if session.is_empty():
            if not messagebox.askyesno(
                "Nothing entered",
                "Every field is blank. Save an empty entry anyway?",
                parent=self.root,
            ):
                return
        self.saved_session = self.repository.add(session)
        if self.on_saved:
            self.on_saved(self.saved_session)
        self.close()


class HistoryWindow(BaseWindow):
    """Browse, search, export, and delete past sessions."""

    title_text = "Session history"
    width = 940
    height = 660

    def __init__(self, repository: SessionRepository, fields: list[FieldSpec],
                 exporters, theme: str = "dark") -> None:
        self.repository = repository
        self.fields = fields
        self.exporters = exporters
        self.sessions: list[Session] = []
        super().__init__(theme)

    def build(self) -> None:
        toolbar = ttk.Frame(self.body, style="App.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text="Search").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        entry.pack(side="left", ipady=3)
        entry.bind("<KeyRelease>", lambda _e: self.refresh())
        ttk.Button(toolbar, text="Export…",
                   command=self.export).pack(side="right")
        ttk.Button(toolbar, text="Delete selected",
                   command=self.delete_selected).pack(side="right", padx=6)

        panes = ttk.PanedWindow(self.body, orient="horizontal")
        panes.pack(fill="both", expand=True)

        left = ttk.Frame(panes, style="App.TFrame")
        self.listbox = tk.Listbox(
            left, activestyle="none", relief="flat", borderwidth=0,
            bg=self.palette["surface"], fg=self.palette["text"],
            selectbackground=self.palette["accent"],
            selectforeground="#10130f", highlightthickness=0,
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self.show_selected())
        panes.add(left, weight=1)

        right = ttk.Frame(panes, style="App.TFrame")
        self.detail = self._make_text(right, height=30, readonly=True)
        self.detail.pack(fill="both", expand=True)
        self.detail.configure(state="disabled")
        panes.add(right, weight=2)

        self.status = ttk.Label(self.body, text="", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=(8, 0))
        self.refresh()

    # data

    def refresh(self) -> None:
        self.sessions = self.repository.search(self.search_var.get())
        self.listbox.delete(0, "end")
        for session in self.sessions:
            self.listbox.insert("end", session.summary_line(self.fields))
        total = self.repository.count()
        minutes = self.repository.total_minutes()
        hours = minutes // 60
        self.status.configure(
            text=f"{len(self.sessions)} shown · {total} logged"
                 + (f" · {hours}h tracked" if hours else "")
        )
        if self.sessions:
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(0)
            self.show_selected()
        else:
            self._render_detail(None)

    def _selected(self) -> Session | None:
        selection = self.listbox.curselection()
        return self.sessions[selection[0]] if selection else None

    def show_selected(self) -> None:
        self._render_detail(self._selected())

    def _render_detail(self, session: Session | None) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if session is None:
            self.detail.insert("end", "\n  Nothing to show.", ("muted",))
        else:
            stamp = f"{session.logged_at:%A %d %B %Y, %H:%M}"
            if session.playtime_text:
                stamp += f"  ·  {session.playtime_text}"
            self.detail.insert("end", f"{stamp}\n\n", ("muted",))
            for label, value in session.as_blocks(self.fields):
                self.detail.insert("end", f"{label}\n", ("heading",))
                self.detail.insert("end", f"{value}\n\n")
        self.detail.configure(state="disabled")

    # actions

    def delete_selected(self) -> None:
        session = self._selected()
        if session is None or session.id is None:
            return
        if messagebox.askyesno(
            "Delete session",
            "Delete this session permanently?", parent=self.root
        ):
            self.repository.delete(session.id)
            self.refresh()

    def export(self) -> None:
        formats = self.exporters.names()
        choice = ExportDialog(self.root, formats, self.palette).ask()
        if not choice:
            return
        exporter = self.exporters.get(choice)
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=exporter.extension,
            initialfile=f"sims-journal{exporter.extension}",
            filetypes=[(choice.title(), f"*{exporter.extension}"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        content = exporter.render(self.repository.all())
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        messagebox.showinfo("Exported", f"Saved to:\n{path}",
                            parent=self.root)


class ExportDialog:
    """Small modal asking which export format to use."""

    def __init__(self, parent: tk.Misc, formats: list[str],
                 palette: dict[str, str]) -> None:
        self.choice: str | None = None
        self.top = tk.Toplevel(parent)
        self.top.title("Export format")
        self.top.configure(bg=palette["bg"])
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)

        frame = ttk.Frame(self.top, padding=18, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Choose a format:").pack(anchor="w",
                                                      pady=(0, 8))
        self.var = tk.StringVar(value=formats[0])
        for name in formats:
            ttk.Radiobutton(frame, text=name.title(), value=name,
                            variable=self.var).pack(anchor="w")
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Export", style="Accent.TButton",
                   command=self._confirm).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Cancel",
                   command=self.top.destroy).pack(side="right")

    def _confirm(self) -> None:
        self.choice = self.var.get()
        self.top.destroy()

    def ask(self) -> str | None:
        self.top.wait_window()
        return self.choice


class HomeWindow(BaseWindow):
    """The window you get when you double-click the app.

    Exists because a background watcher with no window looks broken: the
    natural reaction to "nothing happened" is to launch it again, which
    used to just pile up refused instances. Double-clicking now always
    shows something, and every feature is one button away.

    Rather than driving the app itself, this window records the player's
    choice in `self.action` and closes; TrackerApp reads it and dispatches.
    That keeps Tk out of the orchestration layer.
    """

    title_text = "Sims Forever Tracker"
    width = 620
    height = 620

    def __init__(self, session: Session | None, fields: list[FieldSpec],
                 theme: str = "dark", stats: str = "",
                 watching: bool = False) -> None:
        self.session = session
        self.fields = fields
        self.stats = stats
        self.watching = watching
        self.action: str | None = None
        self.detected: list[str] = []
        super().__init__(theme)

    def build(self) -> None:
        ttk.Label(self.body, text="Sims Forever Tracker",
                  style="Heading.TLabel").pack(anchor="w")
        status = ("Watching for The Sims 4 in the background."
                  if self.watching else
                  "Not currently watching for the game.")
        ttk.Label(self.body, text=status,
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 14))

        # last session preview
        if self.session is None:
            preview_text = ("No sessions logged yet.\n\n"
                            "Play, then log what happened — next time you "
                            "open this, it'll be waiting for you here.")
        else:
            preview_text = ""
        ttk.Label(self.body, text="Where you left off",
                  style="Field.TLabel").pack(anchor="w")

        preview = self._make_text(self.body, height=12, readonly=True)
        preview.pack(fill="both", expand=True, pady=(4, 14))
        if self.session is None:
            preview.insert("end", preview_text, ("muted",))
        else:
            stamp = f"{self.session.logged_at:%A %d %B, %H:%M}"
            if self.session.playtime_text:
                stamp += f"  ·  played {self.session.playtime_text}"
            preview.insert("end", f"{stamp}\n\n", ("muted",))
            for label, value in self.session.as_blocks(self.fields):
                preview.insert("end", f"{label}\n", ("heading",))
                preview.insert("end", f"{value}\n\n")
        preview.configure(state="disabled")

        # actions
        buttons = ttk.Frame(self.body, style="App.TFrame")
        buttons.pack(fill="x")

        primary = ("Start watching" if not self.watching
                   else "Watching — keep running")
        ttk.Button(buttons, text=primary, style="Accent.TButton",
                   command=lambda: self._choose("watch")).pack(
                       side="left", padx=(0, 8))
        ttk.Button(buttons, text="Log a session",
                   command=lambda: self._choose("log")).pack(
                       side="left", padx=(0, 8))
        ttk.Button(buttons, text="History",
                   command=lambda: self._choose("history")).pack(
                       side="left", padx=(0, 8))
        ttk.Button(buttons, text="Detect my game",
                   command=self.detect).pack(side="left")

        self.hint = ttk.Label(self.body, text=self.stats, style="Muted.TLabel")
        self.hint.pack(anchor="w", pady=(12, 0))

    def _choose(self, action: str) -> None:
        self.action = action
        self.close()

    def detect(self) -> None:
        """Scan running processes for anything that looks like the game."""
        from .watcher import GameWatcher

        self.detected = GameWatcher.detect_candidates()
        if not self.detected:
            messagebox.showinfo(
                "Nothing found",
                "No running process looked like The Sims.\n\n"
                "Start the game first, then try again — detection only "
                "works while it's open.",
                parent=self.root,
            )
            return
        listed = "\n".join(f"  · {name}" for name in self.detected)
        if messagebox.askyesno(
            "Game detected",
            f"Found:\n\n{listed}\n\nAdd these to your watch list?",
            parent=self.root,
        ):
            self.action = "save_detected"
            self.close()