import json
import math
import sys
import uuid
import ctypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


APP_DIR = Path.home() / "AppData" / "Local" / "ProgressDesk"
DATA_FILE = APP_DIR / "tasks.json"
SETTINGS_FILE = APP_DIR / "settings.json"
ICON_FILE = Path(__file__).with_name("assets") / "progressdesk_icon.png"
CURRENT_FILTER = "Current"
WATCHLIST_FILTER = "To Watch"
CATEGORY_FILTERS = (CURRENT_FILTER, WATCHLIST_FILTER, "Movies", "Series", "Learning", "Reading", "Custom", "Complete")
STARTUP_APP_NAME = "ProgressDesk"
DEFAULT_SETTINGS = {
    "start_on_windows_startup": True,
    "personal_watchlist_seeded": False,
}

WATCHLIST_ITEMS = (
    ("Jojo Rabbit", "Movies", 1, 0, "movies", 0, ""),
    ("Bugonia", "Movies", 1, 0, "movies", 0, ""),
    ("Obsession", "Movies", 1, 0, "movies", 0, ""),
    ("Send Help", "Movies", 1, 0, "movies", 0, ""),
    ("Exit 8", "Movies", 1, 0, "movies", 0, ""),
    ("The Bone Temple", "Movies", 1, 0, "movies", 0, ""),
    ("Hokum", "Movies", 1, 0, "movies", 0, ""),
    ("We Bury the Dead", "Movies", 1, 0, "movies", 0, ""),
    ("Primate", "Movies", 1, 0, "movies", 0, ""),
    ("Undertone", "Movies", 1, 0, "movies", 0, ""),
    ("War and Peace (1966)", "Movies", 1, 0, "movies", 0, ""),
    ("Behind Her Eyes", "Movies", 1, 0, "movies", 0, ""),
    ("The Fall", "Movies", 1, 0, "movies", 0, ""),
    ("Revenge (2007)", "Movies", 1, 0, "movies", 0, ""),
    ("City of God", "Movies", 1, 1, "movies", 0, "Watched."),
    ("Warrior", "Movies", 1, 0, "movies", 0, "Tom Hardy."),
    ("Big Fish", "Movies", 1, 0, "movies", 0, ""),
    ("Ex Machina", "Movies", 1, 0, "movies", 0, ""),
    ("Sisu", "Movies", 1, 0, "movies", 0, "2022 Finnish movie."),
    ("Requiem for a Dream", "Movies", 1, 0, "movies", 0, ""),
    ("Dancer in the Dark", "Movies", 1, 0, "movies", 0, ""),
    ("I Spit on Your Grave", "Movies", 1, 0, "movies", 0, ""),
    ("Iratta", "Movies", 1, 0, "movies", 0, ""),
    ("No Mercy", "Movies", 1, 0, "movies", 0, "Korean."),
    ("Sorcerer", "Movies", 1, 0, "movies", 0, ""),
    ("Widow's Bay", "Series", 10, 0, "episodes", 0, ""),
    ("Devs", "Series", 8, 0, "episodes", 0, ""),
    ("From", "Series", 10, 0, "episodes", 0, ""),
    ("1899", "Series", 8, 0, "episodes", 0, ""),
    ("The Peripheral", "Series", 8, 0, "episodes", 0, ""),
)


COLORS = {
    "bg": "#f7f6f2",
    "surface": "#ffffff",
    "surface_2": "#efede7",
    "text": "#1d1c1a",
    "muted": "#514d47",
    "line": "#ddd8ce",
    "accent": "#287c68",
    "accent_2": "#dceee8",
    "danger": "#b64b4b",
    "complete": "#4a8f5d",
}


def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = (
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    )
    canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)


def enable_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except OSError:
            windll.user32.SetProcessDPIAware()
    except (AttributeError, ImportError, OSError):
        pass


@dataclass
class Task:
    id: str
    title: str
    category: str
    total_units: int
    completed_units: int
    unit_name: str
    estimate_seconds: int
    spent_seconds: int = 0
    timer_started_at: str | None = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: now_iso())
    completed_at: str | None = None

    @classmethod
    def from_dict(cls, data):
        task = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "Untitled"),
            category=data.get("category", "Learning"),
            total_units=max(1, int(data.get("total_units", 1))),
            completed_units=max(0, int(data.get("completed_units", 0))),
            unit_name=data.get("unit_name", "parts"),
            estimate_seconds=max(0, int(data.get("estimate_seconds", 0))),
            spent_seconds=max(0, int(data.get("spent_seconds", 0))),
            timer_started_at=data.get("timer_started_at"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", now_iso()),
            completed_at=data.get("completed_at"),
        )
        task.completed_units = min(task.completed_units, task.total_units)
        task.sync_completion_state()
        return task

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "total_units": self.total_units,
            "completed_units": min(self.completed_units, self.total_units),
            "unit_name": self.unit_name,
            "estimate_seconds": self.estimate_seconds,
            "spent_seconds": self.current_spent_seconds(),
            "timer_started_at": self.timer_started_at,
            "notes": self.notes,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def current_spent_seconds(self):
        if not self.timer_started_at:
            return self.spent_seconds
        return self.spent_seconds + seconds_since(self.timer_started_at)

    def remaining_seconds(self):
        if self.estimate_seconds <= 0:
            return None
        return max(0, self.estimate_seconds - self.current_spent_seconds())

    def progress(self):
        return min(1.0, self.completed_units / self.total_units)

    def is_complete(self):
        return self.completed_units >= self.total_units

    def is_to_watch(self):
        return (
            self.category in ("Movies", "Series")
            and not self.is_complete()
            and self.completed_units == 0
            and self.spent_seconds == 0
            and self.timer_started_at is None
        )

    def sync_completion_state(self):
        if self.is_complete():
            if self.is_running():
                self.spent_seconds = self.current_spent_seconds()
                self.timer_started_at = None
            if not self.completed_at:
                self.completed_at = now_iso()
        else:
            self.completed_at = None

    def is_running(self):
        return self.timer_started_at is not None


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def seconds_since(iso_string):
    try:
        started = datetime.fromisoformat(iso_string)
    except (TypeError, ValueError):
        return 0
    return max(0, int((datetime.now(timezone.utc) - started).total_seconds()))


def format_duration(seconds):
    if seconds is None:
        return "No estimate"
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes}m"
    return "0m"


def normalized_title(title):
    return " ".join(title.strip().lower().split())


def category_defaults(category):
    values = {
        "Learning": ("parts", 5),
        "Series": ("episodes", 10),
        "Movies": ("movies", 1),
        "Reading": ("chapters", 12),
        "Custom": ("steps", 5),
    }
    return values.get(category, values["Custom"])


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    if not SETTINGS_FILE.exists():
        return settings
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return settings
    if isinstance(raw, dict):
        settings.update({key: raw[key] for key in DEFAULT_SETTINGS.keys() & raw.keys()})
    return settings


def save_settings(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(DEFAULT_SETTINGS)
    payload.update(settings)
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class WindowsStartup:
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def is_supported():
        return sys.platform == "win32"

    @staticmethod
    def command():
        launcher = Path(__file__).with_name("ProgressDesk.pyw")
        executable = Path(sys.executable)
        if executable.name.lower() == "python.exe":
            pythonw = executable.with_name("pythonw.exe")
            if pythonw.exists():
                executable = pythonw
        return f'"{executable}" "{launcher}" --startup'

    @classmethod
    def read_entry(cls):
        if not cls.is_supported():
            return None
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_READ) as key:
                value, _value_type = winreg.QueryValueEx(key, STARTUP_APP_NAME)
                return value
        except (FileNotFoundError, OSError):
            return None

    @classmethod
    def is_enabled(cls):
        return cls.read_entry() == cls.command()

    @classmethod
    def enable(cls):
        if not cls.is_supported():
            return False
        try:
            import winreg

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY) as key:
                winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, cls.command())
            return True
        except OSError:
            return False

    @classmethod
    def disable(cls):
        if not cls.is_supported():
            return False
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, STARTUP_APP_NAME)
            return True
        except FileNotFoundError:
            return True
        except OSError:
            return False

    @classmethod
    def sync(cls, enabled):
        return cls.enable() if enabled else cls.disable()


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        bg,
        fg,
        activebackground=None,
        activeforeground=None,
        font=("Segoe UI", 10, "bold"),
        padx=14,
        pady=8,
        radius=8,
        width=None,
        height=None,
    ):
        self.command = command
        self.text = text
        self.bg_color = bg
        self.fg_color = fg
        self.active_bg = activebackground or bg
        self.active_fg = activeforeground or fg
        self.font = font
        self.radius = radius
        self.is_hovered = False

        text_font = tkfont.Font(font=font)
        measured_width = text_font.measure(text) + (padx * 2)
        measured_height = text_font.metrics("linespace") + (pady * 2)
        self.button_width = width or measured_width
        self.button_height = height or measured_height

        super().__init__(
            parent,
            width=self.button_width,
            height=self.button_height,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )

        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<Button-1>", self._on_click, add="+")
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self._draw()

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        handled = {"bg", "fg", "activebackground", "activeforeground", "text"}
        for key in handled & options.keys():
            value = options.pop(key)
            if key == "bg":
                self.bg_color = value
            elif key == "fg":
                self.fg_color = value
            elif key == "activebackground":
                self.active_bg = value
            elif key == "activeforeground":
                self.active_fg = value
            elif key == "text":
                self.text = value
        if options:
            super().configure(**options)
        self._draw()

    config = configure

    def _on_enter(self, _event):
        self.is_hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.is_hovered = False
        self._draw()

    def _on_click(self, _event):
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        width = max(1, self.winfo_width() or self.button_width)
        height = max(1, self.winfo_height() or self.button_height)
        bg = self.active_bg if self.is_hovered else self.bg_color
        fg = self.active_fg if self.is_hovered else self.fg_color
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, self.radius, fill=bg, outline="")
        self.create_text(width / 2, height / 2, text=self.text, fill=fg, font=self.font)


class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg, parent_bg=None, border=None, radius=8, padx=0, pady=0):
        self.fill = bg
        self.border = border
        self.radius = radius
        self.padx = padx
        self.pady = pady
        super().__init__(
            parent,
            bg=parent_bg or parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        self.content = tk.Frame(self, bg=bg)
        self.content_window = self.create_window(
            self.padx,
            self.pady,
            window=self.content,
            anchor="nw",
        )
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self.content.bind("<Configure>", lambda _event: self._sync_size(), add="+")

    def _sync_size(self):
        width = self.content.winfo_reqwidth() + (self.padx * 2)
        height = self.content.winfo_reqheight() + (self.pady * 2)
        self.configure(width=width, height=height)
        self._draw()

    def _draw(self):
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.delete("shape")
        outline = self.border or self.fill
        draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill=self.fill,
            outline=outline,
            tags="shape",
        )
        self.tag_lower("shape")
        self.itemconfigure(
            self.content_window,
            width=max(1, width - (self.padx * 2)),
            height=max(1, height - (self.pady * 2)),
        )


class RoundedLabel(tk.Canvas):
    def __init__(self, parent, text="", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 10), padx=16, pady=11, radius=8):
        self.text = text
        self.fill = bg
        self.fg = fg
        self.text_font = font
        self.padx = padx
        self.pady = pady
        self.radius = radius
        metrics_font = tkfont.Font(font=font)
        width = metrics_font.measure(text or " ") + (padx * 2)
        height = metrics_font.metrics("linespace") + (pady * 2)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self._draw()

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        for key in ("text", "bg", "fg", "font"):
            if key in options:
                value = options.pop(key)
                if key == "text":
                    self.text = value
                elif key == "bg":
                    self.fill = value
                elif key == "fg":
                    self.fg = value
                elif key == "font":
                    self.text_font = value
        if options:
            super().configure(**options)
        self._draw()

    config = configure

    def _draw(self):
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, self.radius, fill=self.fill, outline="")
        self.create_text(self.padx, height / 2, text=self.text, fill=self.fg, font=self.text_font, anchor="w")


class RoundedEntry(tk.Canvas):
    def __init__(self, parent, textvariable, radius=8, width=240, placeholder=""):
        self.radius = radius
        self.placeholder = placeholder
        super().__init__(
            parent,
            width=width,
            height=38,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 10),
        )
        self.entry_window = self.create_window(14, 19, window=self.entry, anchor="w")
        self.placeholder_id = self.create_text(
            14,
            19,
            text=self.placeholder,
            fill=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            state="hidden",
        )
        self.bind("<Button-1>", lambda _event: self.focus_set(), add="+")
        self.entry.bind("<FocusIn>", lambda _event: self.refresh_placeholder(), add="+")
        self.entry.bind("<FocusOut>", lambda _event: self.refresh_placeholder(), add="+")
        textvariable.trace_add("write", lambda *_: self.refresh_placeholder())
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self._draw()
        self.refresh_placeholder()

    def _draw(self):
        self.delete("shape")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill=COLORS["surface"],
            outline=COLORS["line"],
            tags="shape",
        )
        self.tag_lower("shape")
        self.coords(self.entry_window, 14, height / 2)
        self.coords(self.placeholder_id, 14, height / 2)
        self.itemconfigure(self.entry_window, width=max(1, width - 28))
        self.itemconfigure(self.placeholder_id, width=max(1, width - 28))

    def refresh_placeholder(self):
        has_text = bool(self.entry.get().strip())
        is_focused = self.entry == self.focus_get()
        state = "hidden" if has_text or is_focused or not self.placeholder else "normal"
        self.itemconfigure(self.placeholder_id, state=state)

    def insert(self, *args):
        return self.entry.insert(*args)

    def get(self):
        return self.entry.get()

    def focus_set(self):
        return self.entry.focus_set()


class RoundedText(tk.Canvas):
    def __init__(self, parent, height=4, width=36, radius=8):
        self.radius = radius
        text_font = tkfont.Font(font=("Segoe UI", 10))
        pixel_width = text_font.measure("0" * width) + 28
        pixel_height = (text_font.metrics("linespace") * height) + 18
        super().__init__(
            parent,
            width=pixel_width,
            height=pixel_height,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        self.text = tk.Text(
            self,
            height=height,
            width=width,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg="#fbfaf7",
            fg=COLORS["text"],
            font=("Segoe UI", 10),
        )
        self.text_window = self.create_window(12, 9, window=self.text, anchor="nw")
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self._draw()

    def _draw(self):
        self.delete("shape")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill="#fbfaf7",
            outline=COLORS["line"],
            tags="shape",
        )
        self.tag_lower("shape")
        self.itemconfigure(self.text_window, width=max(1, width - 24), height=max(1, height - 18))

    def insert(self, *args):
        return self.text.insert(*args)

    def get(self, *args):
        return self.text.get(*args)


class TaskStore:
    def __init__(self, path):
        self.path = path
        self.tasks: list[Task] = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.tasks = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.tasks = [Task.from_dict(item) for item in raw]
        except (json.JSONDecodeError, OSError, TypeError):
            self.tasks = []

    def save(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        payload = [task.to_dict() for task in self.tasks]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, task):
        self.tasks.insert(0, task)
        self.save()

    def add_missing_watchlist_items(self, items):
        existing = {
            (normalized_title(task.title), task.category)
            for task in self.tasks
        }
        new_tasks = []
        for title, category, total_units, completed_units, unit_name, estimate_seconds, notes in items:
            key = (normalized_title(title), category)
            if key in existing:
                continue
            task = Task(
                id=str(uuid.uuid4()),
                title=title,
                category=category,
                total_units=total_units,
                completed_units=completed_units,
                unit_name=unit_name,
                estimate_seconds=estimate_seconds,
                spent_seconds=0,
                timer_started_at=None,
                notes=notes,
                created_at=now_iso(),
            )
            task.sync_completion_state()
            new_tasks.append(task)
            existing.add(key)
        if new_tasks:
            self.tasks = new_tasks + self.tasks
            self.save()
        return len(new_tasks)

    def delete(self, task_id):
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self.save()

    def get(self, task_id):
        return next((task for task in self.tasks if task.id == task_id), None)


class TaskDialog(tk.Toplevel):
    def __init__(self, parent, task=None):
        super().__init__(parent)
        self.title("Task")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.result = None
        self.task = task

        self.transient(parent)
        self.grab_set()

        self.title_var = tk.StringVar(value=task.title if task else "")
        self.category_var = tk.StringVar(value=task.category if task else "Learning")
        default_unit, default_total = category_defaults(self.category_var.get())
        self.total_var = tk.StringVar(value=str(task.total_units if task else default_total))
        self.completed_var = tk.StringVar(value=str(task.completed_units if task else 0))
        self.unit_var = tk.StringVar(value=task.unit_name if task else default_unit)
        estimate_hours = round((task.estimate_seconds if task else 0) / 3600, 2)
        self.estimate_var = tk.StringVar(value="" if estimate_hours == 0 else str(estimate_hours))
        self.notes_text = None

        self.build()
        self.category_var.trace_add("write", self.apply_category_defaults)
        self.bind("<Return>", lambda _event: self.submit())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(50, lambda: self.title_entry.focus_set())

    def build(self):
        shell = RoundedFrame(self, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=24, pady=22)
        shell.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        body = shell.content

        tk.Label(
            body,
            text="Add progress item" if self.task is None else "Edit progress item",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        self.title_entry = self.field(body, "Title", self.title_var, 1)

        tk.Label(body, text="Category", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="w", pady=(12, 4)
        )
        category = ttk.Combobox(
            body,
            textvariable=self.category_var,
            values=("Learning", "Series", "Movies", "Reading", "Custom"),
            state="readonly",
            width=28,
        )
        category.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.field(body, "Total", self.total_var, 5, width=12)
        self.field(body, "Completed", self.completed_var, 5, column=1, width=12)
        self.field(body, "Unit name", self.unit_var, 7)
        self.field(body, "Estimated hours", self.estimate_var, 9)

        tk.Label(body, text="Notes", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=11, column=0, sticky="w", pady=(12, 4)
        )
        self.notes_text = RoundedText(
            body,
            height=4,
            width=36,
            radius=8,
        )
        self.notes_text.grid(row=12, column=0, columnspan=2, sticky="ew")
        if self.task:
            self.notes_text.insert("1.0", self.task.notes)

        actions = tk.Frame(body, bg=COLORS["surface"])
        actions.grid(row=13, column=0, columnspan=2, sticky="e", pady=(18, 0))
        self.text_button(actions, "Cancel", self.destroy, secondary=True).pack(side="left", padx=(0, 8))
        self.text_button(actions, "Save", self.submit).pack(side="left")

    def field(self, parent, label, variable, row, column=0, width=30):
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=column, sticky="w", pady=(12, 4), padx=(0 if column == 0 else 12, 0)
        )
        entry = RoundedEntry(
            parent,
            textvariable=variable,
            width=max(120, width * 9),
            radius=8,
        )
        entry.grid(
            row=row + 1,
            column=column,
            sticky="ew",
            padx=(0 if column == 0 else 12, 0),
        )
        return entry

    def text_button(self, parent, text, command, secondary=False):
        bg = COLORS["surface_2"] if secondary else COLORS["accent"]
        fg = COLORS["text"] if secondary else "#ffffff"
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=COLORS["line"] if secondary else "#216957",
            activeforeground=fg,
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            radius=8,
        )

    def apply_category_defaults(self, *_args):
        unit_name, total_units = category_defaults(self.category_var.get())
        if not self.unit_var.get().strip():
            self.unit_var.set(unit_name)
        if not self.total_var.get().strip():
            self.total_var.set(str(total_units))

    def submit(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Please enter a title.")
            return
        try:
            total_units = max(1, int(self.total_var.get()))
            completed_units = max(0, int(self.completed_var.get()))
            completed_units = min(completed_units, total_units)
            estimate_hours = float(self.estimate_var.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid values", "Total, completed, and estimate must be numbers.")
            return

        self.result = {
            "title": title,
            "category": self.category_var.get(),
            "total_units": total_units,
            "completed_units": completed_units,
            "unit_name": self.unit_var.get().strip() or "steps",
            "estimate_seconds": max(0, int(estimate_hours * 3600)),
            "notes": self.notes_text.get("1.0", "end").strip(),
        }
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.status_var = tk.StringVar()
        self.startup_button = None

        self.build()
        self.refresh()
        self.bind("<Escape>", lambda _event: self.destroy())

    def build(self):
        shell = RoundedFrame(self, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=24, pady=22)
        shell.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        body = shell.content

        tk.Label(
            body,
            text="Settings",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            body,
            text="Windows startup",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=(18, 4))
        tk.Label(
            body,
            textvariable=self.status_var,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=380,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

        actions = tk.Frame(body, bg=COLORS["surface"])
        actions.grid(row=3, column=0, sticky="e", pady=(18, 0))
        self.startup_button = RoundedButton(
            actions,
            text="",
            command=self.toggle_startup,
            bg=COLORS["accent"],
            fg="#ffffff",
            activebackground="#216957",
            activeforeground="#ffffff",
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            radius=8,
        )
        self.startup_button.pack(side="left", padx=(0, 8))
        RoundedButton(
            actions,
            text="Close",
            command=self.destroy,
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            activebackground=COLORS["line"],
            activeforeground=COLORS["text"],
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            radius=8,
        ).pack(side="left")

    def refresh(self):
        if not WindowsStartup.is_supported():
            self.status_var.set("Startup control is only available on Windows.")
            self.startup_button.configure(text="Unavailable", bg=COLORS["surface_2"], fg=COLORS["muted"])
            return

        enabled = WindowsStartup.is_enabled()
        self.status_var.set(
            "ProgressDesk opens automatically when you sign in to Windows."
            if enabled
            else "ProgressDesk does not open automatically when you sign in to Windows."
        )
        self.startup_button.configure(
            text="Disable startup" if enabled else "Enable startup",
            bg=COLORS["danger"] if enabled else COLORS["accent"],
            fg="#ffffff",
            activebackground="#963c3c" if enabled else "#216957",
            activeforeground="#ffffff",
        )

    def toggle_startup(self):
        enabled = WindowsStartup.is_enabled()
        desired = not enabled
        if not WindowsStartup.sync(desired):
            messagebox.showerror("Startup setting", "Could not update the Windows startup setting.")
            return
        self.parent.settings["start_on_windows_startup"] = desired
        save_settings(self.parent.settings)
        self.refresh()


class ProgressDesk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ProgressDesk")
        self.configure_fonts()
        self.geometry("1040x700")
        self.minsize(880, 560)
        self.configure(bg=COLORS["bg"])

        self.store = TaskStore(DATA_FILE)
        self.settings = load_settings()
        self.seed_personal_watchlist()
        self.filter_var = tk.StringVar(value=CURRENT_FILTER)
        self.search_var = tk.StringVar(value="")
        self.cards = {}
        self.icon_image = None
        self._shutdown_prompt_active = False
        self._original_wndproc = None
        self._wndproc_callback = None

        self.setup_styles()
        self.setup_icon()
        self.sync_startup_setting()
        self.build_layout()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.install_shutdown_prompt()
        self.render()
        self.tick()

    def seed_personal_watchlist(self):
        if self.settings.get("personal_watchlist_seeded"):
            return
        self.store.add_missing_watchlist_items(WATCHLIST_ITEMS)
        self.settings["personal_watchlist_seeded"] = True
        save_settings(self.settings)

    def configure_fonts(self):
        base_font = tkfont.nametofont("TkDefaultFont")
        base_font.configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkTextFont").configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkMenuFont").configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkHeadingFont").configure(family="Segoe UI", size=10, weight="bold")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=COLORS["surface_2"],
            background=COLORS["accent"],
            bordercolor=COLORS["surface_2"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
            thickness=9,
        )
        style.configure(
            "Completed.Horizontal.TProgressbar",
            troughcolor=COLORS["surface_2"],
            background=COLORS["complete"],
            bordercolor=COLORS["surface_2"],
            lightcolor=COLORS["complete"],
            darkcolor=COLORS["complete"],
            thickness=9,
        )

    def setup_icon(self):
        if not ICON_FILE.exists():
            return
        try:
            self.icon_image = tk.PhotoImage(file=str(ICON_FILE))
            self.iconphoto(True, self.icon_image)
        except tk.TclError:
            self.icon_image = None

    def sync_startup_setting(self):
        if not WindowsStartup.is_supported():
            return
        desired = bool(self.settings.get("start_on_windows_startup", True))
        WindowsStartup.sync(desired)

    def install_shutdown_prompt(self):
        if sys.platform != "win32":
            return
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(self.winfo_id())
        gwlp_wndproc = -4
        wm_queryendsession = 0x0011
        wm_endsession = 0x0016

        wndproc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        try:
            set_window_long = user32.SetWindowLongPtrW
        except AttributeError:
            set_window_long = user32.SetWindowLongW
        set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_window_long.restype = ctypes.c_ssize_t
        user32.CallWindowProcW.argtypes = [
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t

        def wndproc(window, message, wparam, lparam):
            if message == wm_queryendsession:
                return self.handle_shutdown_query(window)
            if message == wm_endsession and int(wparam):
                self.store.save()
            if not self._original_wndproc:
                return user32.DefWindowProcW(window, message, wparam, lparam)
            return user32.CallWindowProcW(self._original_wndproc, window, message, wparam, lparam)

        self._wndproc_callback = wndproc_type(wndproc)
        self._original_wndproc = set_window_long(
            hwnd,
            gwlp_wndproc,
            ctypes.cast(self._wndproc_callback, ctypes.c_void_p).value,
        )
        if not self._original_wndproc:
            self._wndproc_callback = None

    def handle_shutdown_query(self, hwnd):
        if self._shutdown_prompt_active:
            return 1
        self._shutdown_prompt_active = True
        self.store.save()

        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.update()
        except tk.TclError:
            pass

        user32 = ctypes.windll.user32
        mb_yesno = 0x00000004
        mb_iconquestion = 0x00000020
        mb_systemmodal = 0x00001000
        id_yes = 6
        result = user32.MessageBoxW(
            hwnd,
            "Windows is shutting down. Do you want to review ProgressDesk before shutdown?\n\n"
            "Choose Yes to cancel shutdown and keep ProgressDesk open. Choose No to continue shutdown.",
            "ProgressDesk",
            mb_yesno | mb_iconquestion | mb_systemmodal,
        )
        self._shutdown_prompt_active = False
        return 0 if result == id_yes else 1

    def close_app(self):
        self.store.save()
        self.destroy()

    def build_layout(self):
        header = tk.Frame(self, bg=COLORS["bg"], padx=28, pady=24)
        header.pack(fill="x")

        title_area = tk.Frame(header, bg=COLORS["bg"])
        title_area.pack(side="left")
        tk.Label(
            title_area,
            text="ProgressDesk",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_area,
            text="Track learning plans, watchlists, and long-running goals.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        self.add_button = self.icon_button(header, "+", self.open_add_dialog, "Add item", filled=True)
        self.add_button.pack(side="right", padx=(12, 0))
        self.settings_button = self.icon_button(header, "S", self.open_settings, "Settings")
        self.settings_button.pack(side="right")

        body = tk.Frame(self, bg=COLORS["bg"], padx=28, pady=4)
        body.pack(fill="both", expand=True)

        sidebar_shell = RoundedFrame(
            body,
            bg=COLORS["surface"],
            parent_bg=COLORS["bg"],
            border=COLORS["line"],
            radius=8,
            padx=16,
            pady=16,
        )
        sidebar_shell.pack(side="left", fill="y", padx=(0, 18))
        sidebar = sidebar_shell.content

        tk.Label(
            sidebar,
            text="Views",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        primary_filters = (CURRENT_FILTER, WATCHLIST_FILTER, "Movies", "Series")
        secondary_filters = ("Learning", "Reading", "Custom")
        utility_filters = ("Complete",)

        for label in primary_filters:
            button = RoundedButton(
                sidebar,
                text=label,
                command=lambda value=label: self.set_filter(value),
                bg=COLORS["surface_2"],
                fg=COLORS["text"],
                activebackground=COLORS["line"],
                activeforeground=COLORS["text"],
                width=164,
                padx=14,
                pady=9,
                font=("Segoe UI", 10, "bold"),
                radius=8,
            )
            button.pack(fill="x", pady=(0, 8))
            setattr(self, f"filter_{label}", button)

        tk.Frame(sidebar, bg=COLORS["line"], height=1).pack(fill="x", pady=(6, 12))

        for label in secondary_filters:
            button = RoundedButton(
                sidebar,
                text=label,
                command=lambda value=label: self.set_filter(value),
                bg=COLORS["surface_2"],
                fg=COLORS["text"],
                activebackground=COLORS["line"],
                activeforeground=COLORS["text"],
                width=164,
                padx=14,
                pady=9,
                font=("Segoe UI", 10, "bold"),
                radius=8,
            )
            button.pack(fill="x", pady=(0, 8))
            setattr(self, f"filter_{label}", button)

        tk.Frame(sidebar, bg=COLORS["surface"], height=8).pack(fill="x", expand=True)

        for label in utility_filters:
            button = RoundedButton(
                sidebar,
                text=label,
                command=lambda value=label: self.set_filter(value),
                bg=COLORS["surface_2"],
                fg=COLORS["text"],
                activebackground=COLORS["line"],
                activeforeground=COLORS["text"],
                width=164,
                padx=14,
                pady=9,
                font=("Segoe UI", 10, "bold"),
                radius=8,
            )
            button.pack(fill="x")
            setattr(self, f"filter_{label}", button)

        main = tk.Frame(body, bg=COLORS["bg"])
        main.pack(side="left", fill="both", expand=True)

        controls = tk.Frame(main, bg=COLORS["bg"])
        controls.pack(fill="x", pady=(0, 12))

        self.search_entry = RoundedEntry(controls, self.search_var, radius=8, placeholder="Search here")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", lambda *_: self.render())

        stats = tk.Frame(main, bg=COLORS["bg"])
        stats.pack(fill="x", pady=(0, 14))
        self.stats_labels = []
        for _ in range(4):
            label = RoundedLabel(
                stats,
                bg=COLORS["surface"],
                fg=COLORS["text"],
                padx=16,
                pady=11,
                font=("Segoe UI", 10, "bold"),
                radius=8,
            )
            label.pack(side="left", fill="x", expand=True, padx=(0, 10))
            self.stats_labels.append(label)

        outer = tk.Frame(main, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.list_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.resize_list_window)
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

    def icon_button(self, parent, text, command, tooltip, filled=False):
        button = RoundedButton(
            parent,
            text=text,
            command=command,
            bg=COLORS["accent"] if filled else COLORS["surface_2"],
            fg="#ffffff" if filled else COLORS["text"],
            activebackground="#216957" if filled else COLORS["line"],
            activeforeground="#ffffff" if filled else COLORS["text"],
            width=38,
            height=36,
            font=("Segoe UI", 14, "bold"),
            radius=9,
        )
        button.bind("<Enter>", lambda _event: self.show_tooltip(button, tooltip), add="+")
        button.bind("<Leave>", lambda _event: self.hide_tooltip(), add="+")
        return button

    def show_tooltip(self, widget, text):
        self.hide_tooltip()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        self.tooltip = tk.Toplevel(self)
        self.tooltip.overrideredirect(True)
        self.tooltip.configure(bg=COLORS["text"])
        tk.Label(
            self.tooltip,
            text=text,
            bg=COLORS["text"],
            fg="#ffffff",
            padx=8,
            pady=4,
            font=("Segoe UI", 8),
        ).pack()
        self.tooltip.geometry(f"+{x}+{y}")

    def hide_tooltip(self):
        tooltip = getattr(self, "tooltip", None)
        if tooltip and tooltip.winfo_exists():
            tooltip.destroy()
        self.tooltip = None

    def resize_list_window(self, event):
        self.canvas.itemconfigure(self.list_window, width=event.width)

    def on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_filter(self, value):
        self.filter_var.set(value)
        self.render()

    def open_settings(self):
        dialog = SettingsDialog(self)
        self.wait_window(dialog)

    def open_add_dialog(self):
        dialog = TaskDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            task = Task(
                id=str(uuid.uuid4()),
                created_at=now_iso(),
                spent_seconds=0,
                timer_started_at=None,
                **dialog.result,
            )
            task.sync_completion_state()
            self.store.add(task)
            self.render()

    def open_edit_dialog(self, task_id):
        task = self.store.get(task_id)
        if not task:
            return
        dialog = TaskDialog(self, task)
        self.wait_window(dialog)
        if dialog.result:
            for key, value in dialog.result.items():
                setattr(task, key, value)
            task.completed_units = min(task.completed_units, task.total_units)
            task.sync_completion_state()
            self.store.save()
            self.render()

    def filtered_tasks(self):
        selected = self.filter_var.get()
        query = self.search_var.get().strip().lower()
        tasks = self.store.tasks
        if selected == "Complete":
            tasks = [task for task in tasks if task.is_complete()]
        elif selected == WATCHLIST_FILTER:
            tasks = [task for task in tasks if task.is_to_watch()]
        elif selected == CURRENT_FILTER:
            tasks = [task for task in tasks if not task.is_complete() and not task.is_to_watch()]
        else:
            tasks = [task for task in tasks if task.category == selected]
            tasks = [task for task in tasks if not task.is_complete()]
        if query:
            tasks = [task for task in tasks if query in task.title.lower() or query in task.notes.lower()]
        return tasks

    def render(self):
        self.update_filter_buttons()
        self.render_stats()
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.cards.clear()

        tasks = self.filtered_tasks()
        if not tasks:
            self.render_empty()
            return

        columns = 2 if self.winfo_width() >= 940 else 1
        for index, task in enumerate(tasks):
            card = self.task_card(self.list_frame, task)
            row = index // columns
            column = index % columns
            card.grid(row=row, column=column, sticky="nsew", padx=(0, 14), pady=(0, 14))
            self.list_frame.grid_columnconfigure(column, weight=1)

    def update_filter_buttons(self):
        selected = self.filter_var.get()
        for label in CATEGORY_FILTERS:
            button = getattr(self, f"filter_{label}")
            active = label == selected
            button.configure(
                bg=COLORS["accent"] if active else COLORS["surface_2"],
                fg="#ffffff" if active else COLORS["text"],
                activebackground="#216957" if active else COLORS["line"],
                activeforeground="#ffffff" if active else COLORS["text"],
            )

    def render_stats(self):
        total = sum(1 for task in self.store.tasks if not task.is_complete() and not task.is_to_watch())
        to_watch = sum(1 for task in self.store.tasks if task.is_to_watch())
        complete = sum(1 for task in self.store.tasks if task.is_complete())
        running = sum(1 for task in self.store.tasks if task.is_running())
        values = (
            f"{total} current item{'s' if total != 1 else ''}",
            f"{to_watch} to watch",
            f"{complete} complete",
            f"{running} timer{'s' if running != 1 else ''} running",
        )
        for label, text in zip(self.stats_labels, values):
            label.configure(text=text)

    def render_empty(self):
        empty = tk.Frame(self.list_frame, bg=COLORS["bg"], pady=80)
        empty.grid(row=0, column=0, sticky="nsew")
        selected = self.filter_var.get()
        empty_text = "No items here yet"
        detail_text = "Add a system design plan, series, movie list, reading goal, or any trackable project."
        if selected == CURRENT_FILTER:
            empty_text = "No current items"
            detail_text = "Start an item from To Watch or add a new progress item."
        elif selected == WATCHLIST_FILTER:
            empty_text = "Nothing to watch yet"
            detail_text = "Add movies or series here, then press Start when you begin."
        tk.Label(
            empty,
            text=empty_text,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack()
        tk.Label(
            empty,
            text=detail_text,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(pady=(6, 18))
        self.text_button(empty, "Add item", self.open_add_dialog).pack()

    def task_card(self, parent, task):
        card = RoundedFrame(parent, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=18, pady=16)
        body = card.content
        body.grid_columnconfigure(0, weight=1)

        top = tk.Frame(body, bg=COLORS["surface"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        tk.Label(
            top,
            text=task.title,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            wraplength=340,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        RoundedLabel(
            top,
            text=task.category,
            bg=COLORS["accent_2"],
            fg=COLORS["accent"],
            padx=9,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            radius=8,
        ).grid(row=0, column=1, sticky="e")

        progress_row = tk.Frame(body, bg=COLORS["surface"])
        progress_row.grid(row=1, column=0, sticky="ew", pady=(14, 5))
        progress_row.grid_columnconfigure(0, weight=1)
        progressbar = ttk.Progressbar(
            progress_row,
            style="Completed.Horizontal.TProgressbar" if task.progress() >= 1 else "Horizontal.TProgressbar",
            maximum=100,
            value=task.progress() * 100,
        )
        progressbar.grid(row=0, column=0, sticky="ew")
        percent_label = tk.Label(
            progress_row,
            text=f"{math.floor(task.progress() * 100)}%",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        percent_label.grid(row=0, column=1, padx=(10, 0))

        meta = tk.Frame(body, bg=COLORS["surface"])
        meta.grid(row=2, column=0, sticky="ew", pady=(6, 12))
        tk.Label(
            meta,
            text=f"{task.completed_units}/{task.total_units} {task.unit_name}",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(side="left")
        remaining_label = tk.Label(
            meta,
            text=f"{format_duration(task.remaining_seconds())} left",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        remaining_label.pack(side="right")

        if task.notes:
            tk.Label(
                body,
                text=task.notes,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
                wraplength=420,
                justify="left",
                anchor="w",
            ).grid(row=3, column=0, sticky="ew", pady=(0, 12))

        actions = tk.Frame(body, bg=COLORS["surface"])
        actions.grid(row=4, column=0, sticky="ew")
        if task.total_units > 1:
            self.small_button(actions, "-1", lambda tid=task.id: self.bump(tid, -1)).pack(side="left")
            self.small_button(actions, "+1", lambda tid=task.id: self.bump(tid, 1)).pack(side="left", padx=(6, 0))
        if not task.is_complete():
            self.small_button(actions, "Complete", lambda tid=task.id: self.mark_complete(tid), accent=True).pack(
                side="left", padx=(6, 0)
            )
        timer_text = "Pause" if task.is_running() else "Start"
        self.small_button(actions, timer_text, lambda tid=task.id: self.toggle_timer(tid), accent=task.is_running()).pack(
            side="left", padx=(10, 0)
        )
        self.small_button(actions, "Edit", lambda tid=task.id: self.open_edit_dialog(tid)).pack(side="right", padx=(6, 0))
        self.small_button(actions, "Delete", lambda tid=task.id: self.delete_task(tid), danger=True).pack(side="right")

        self.cards[task.id] = {
            "remaining": remaining_label,
            "progress": progressbar,
            "percent": percent_label,
        }
        return card

    def text_button(self, parent, text, command):
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=COLORS["accent"],
            fg="#ffffff",
            activebackground="#216957",
            activeforeground="#ffffff",
            padx=18,
            pady=9,
            font=("Segoe UI", 10, "bold"),
            radius=8,
        )

    def small_button(self, parent, text, command, accent=False, danger=False):
        bg = COLORS["surface_2"]
        fg = COLORS["text"]
        if accent:
            bg = COLORS["accent"]
            fg = "#ffffff"
        if danger:
            fg = COLORS["danger"]
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=COLORS["line"] if not accent else "#216957",
            activeforeground=fg,
            padx=12,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            radius=8,
        )

    def bump(self, task_id, amount):
        task = self.store.get(task_id)
        if not task:
            return
        task.completed_units = max(0, min(task.total_units, task.completed_units + amount))
        task.sync_completion_state()
        self.store.save()
        self.render()

    def mark_complete(self, task_id):
        task = self.store.get(task_id)
        if not task:
            return
        task.completed_units = task.total_units
        task.sync_completion_state()
        self.store.save()
        self.render()

    def toggle_timer(self, task_id):
        task = self.store.get(task_id)
        if not task:
            return
        if task.is_running():
            task.spent_seconds = task.current_spent_seconds()
            task.timer_started_at = None
        else:
            task.timer_started_at = now_iso()
        self.store.save()
        self.render()

    def delete_task(self, task_id):
        task = self.store.get(task_id)
        if not task:
            return
        confirmed = messagebox.askyesno("Delete item", f"Delete '{task.title}'?")
        if not confirmed:
            return
        self.store.delete(task_id)
        self.render()

    def tick(self):
        for task in self.store.tasks:
            if not task.is_running():
                continue
            card = self.cards.get(task.id)
            if card:
                card["remaining"].configure(text=f"{format_duration(task.remaining_seconds())} left")
                card["progress"].configure(value=task.progress() * 100)
                card["percent"].configure(text=f"{math.floor(task.progress() * 100)}%")
        self.after(1000, self.tick)


if __name__ == "__main__":
    enable_dpi_awareness()
    app = ProgressDesk()
    app.mainloop()
