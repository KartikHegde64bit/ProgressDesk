import json
import math
import sys
import uuid
import ctypes
import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
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
TASKSETS_FILTER = "Task Sets"
CATEGORY_FILTERS = (
    CURRENT_FILTER,
    TASKSETS_FILTER,
    WATCHLIST_FILTER,
    "Movies",
    "Series",
    "Learning",
    "Reading",
    "Custom",
    "Complete",
)
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


@dataclass
class TaskSetTask:
    id: str
    title: str
    category: str
    total_units: int
    completed_units: int
    unit_name: str
    notes: str = ""

    @classmethod
    def from_dict(cls, data):
        item = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "Untitled"),
            category=data.get("category", "Learning"),
            total_units=max(1, int(data.get("total_units", 1))),
            completed_units=max(0, int(data.get("completed_units", 0))),
            unit_name=data.get("unit_name", "parts"),
            notes=data.get("notes", ""),
        )
        item.completed_units = min(item.completed_units, item.total_units)
        return item

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "total_units": self.total_units,
            "completed_units": min(self.completed_units, self.total_units),
            "unit_name": self.unit_name,
            "notes": self.notes,
        }

    def progress(self):
        return min(1.0, self.completed_units / self.total_units)

    def is_complete(self):
        return self.completed_units >= self.total_units


@dataclass
class TaskSet:
    id: str
    title: str
    start_at: str | None = None
    end_at: str | None = None
    tasks: list[TaskSetTask] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: now_iso())

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "Untitled task set"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            tasks=[TaskSetTask.from_dict(item) for item in data.get("tasks", [])],
            notes=data.get("notes", ""),
            created_at=data.get("created_at", now_iso()),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "tasks": [task.to_dict() for task in self.tasks],
            "notes": self.notes,
            "created_at": self.created_at,
        }

    def task_progress(self):
        if not self.tasks:
            return 0.0
        total = sum(task.total_units for task in self.tasks)
        completed = sum(min(task.completed_units, task.total_units) for task in self.tasks)
        return min(1.0, completed / max(1, total))

    def complete_count(self):
        return sum(1 for task in self.tasks if task.is_complete())

    def time_progress(self):
        start = parse_iso_datetime(self.start_at)
        end = parse_iso_datetime(self.end_at)
        if not start or not end or end <= start:
            return None
        now = datetime.now(timezone.utc)
        return max(0.0, min(1.0, (now - start).total_seconds() / (end - start).total_seconds()))

    def range_label(self):
        start = format_datetime_label(self.start_at)
        end = format_datetime_label(self.end_at)
        if start and end:
            return f"{start} to {end}"
        if end:
            return f"Due {end}"
        if start:
            return f"Starts {start}"
        return "No time range"

    def is_complete(self):
        return bool(self.tasks) and all(task.is_complete() for task in self.tasks)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(iso_string):
    if not iso_string:
        return None
    try:
        value = datetime.fromisoformat(iso_string)
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


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


def format_datetime_label(iso_string):
    value = parse_iso_datetime(iso_string)
    if not value:
        return ""
    local_value = value.astimezone()
    return local_value.strftime("%d %b %Y, %I:%M %p").lstrip("0")


def format_percent(value):
    if value is None:
        return "Optional"
    return f"{math.floor(value * 100)}%"


def parse_date_time(date_text, time_text, default_time="00:00"):
    date_text = date_text.strip()
    time_text = time_text.strip()
    if not date_text and not time_text:
        return None
    if not date_text:
        raise ValueError("Date is required when a time is entered.")
    if not time_text:
        time_text = default_time
    value = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    return value.astimezone().isoformat()


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
        self.task_sets: list[TaskSet] = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.tasks = []
            self.task_sets = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.tasks = [Task.from_dict(item) for item in raw.get("tasks", [])]
                self.task_sets = [TaskSet.from_dict(item) for item in raw.get("task_sets", [])]
            else:
                self.tasks = [Task.from_dict(item) for item in raw]
                self.task_sets = []
        except (json.JSONDecodeError, OSError, TypeError):
            self.tasks = []
            self.task_sets = []

    def save(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "tasks": [task.to_dict() for task in self.tasks],
            "task_sets": [task_set.to_dict() for task_set in self.task_sets],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, task):
        self.tasks.insert(0, task)
        self.save()

    def add_task_set(self, task_set):
        self.task_sets.insert(0, task_set)
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

    def delete_task_set(self, task_set_id):
        self.task_sets = [task_set for task_set in self.task_sets if task_set.id != task_set_id]
        self.save()

    def get(self, task_id):
        return next((task for task in self.tasks if task.id == task_id), None)

    def get_task_set(self, task_set_id):
        return next((task_set for task_set in self.task_sets if task_set.id == task_set_id), None)


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


class DatePickerDialog(tk.Toplevel):
    def __init__(self, parent, initial_text=""):
        super().__init__(parent)
        self.title("Choose date")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        try:
            initial = datetime.strptime(initial_text, "%Y-%m-%d").date()
        except ValueError:
            initial = date.today()
        self.year = initial.year
        self.month = initial.month
        self.header_var = tk.StringVar()
        self.days_frame = None

        self.build()
        self.render_days()
        self.bind("<Escape>", lambda _event: self.destroy())

    def build(self):
        shell = RoundedFrame(self, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=18, pady=16)
        shell.grid(row=0, column=0, padx=14, pady=14)
        body = shell.content

        nav = tk.Frame(body, bg=COLORS["surface"])
        nav.grid(row=0, column=0, sticky="ew")
        RoundedButton(nav, "<", self.previous_month, COLORS["surface_2"], COLORS["text"], width=34, height=30).pack(side="left")
        tk.Label(
            nav,
            textvariable=self.header_var,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
            width=18,
        ).pack(side="left", padx=8)
        RoundedButton(nav, ">", self.next_month, COLORS["surface_2"], COLORS["text"], width=34, height=30).pack(side="left")

        self.days_frame = tk.Frame(body, bg=COLORS["surface"])
        self.days_frame.grid(row=1, column=0, pady=(12, 0))

    def previous_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.render_days()

    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.render_days()

    def choose(self, day):
        self.result = date(self.year, self.month, day).strftime("%Y-%m-%d")
        self.destroy()

    def render_days(self):
        self.header_var.set(f"{calendar.month_name[self.month]} {self.year}")
        for child in self.days_frame.winfo_children():
            child.destroy()
        for column, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            tk.Label(
                self.days_frame,
                text=name,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 8, "bold"),
                width=4,
            ).grid(row=0, column=column, pady=(0, 5))
        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), start=1):
            for column, day in enumerate(week):
                if day == 0:
                    tk.Frame(self.days_frame, bg=COLORS["surface"], width=34, height=28).grid(row=row, column=column)
                    continue
                RoundedButton(
                    self.days_frame,
                    str(day),
                    lambda value=day: self.choose(value),
                    COLORS["surface_2"],
                    COLORS["text"],
                    activebackground=COLORS["line"],
                    width=34,
                    height=28,
                    font=("Segoe UI", 9, "bold"),
                ).grid(row=row, column=column, padx=2, pady=2)


class TaskSetDialog(tk.Toplevel):
    def __init__(self, parent, task_set=None):
        super().__init__(parent)
        self.title("Task set")
        self.configure(bg=COLORS["bg"])
        self.geometry("980x760")
        self.minsize(860, 560)
        self.resizable(True, True)
        self.result = None
        self.task_set = task_set
        self.task_rows = []

        self.transient(parent)
        self.grab_set()

        self.title_var = tk.StringVar(value=task_set.title if task_set else "")
        start = parse_iso_datetime(task_set.start_at) if task_set else None
        end = parse_iso_datetime(task_set.end_at) if task_set else None
        start = start.astimezone() if start else None
        end = end.astimezone() if end else None
        self.start_date_var = tk.StringVar(value=start.strftime("%Y-%m-%d") if start else "")
        self.start_time_var = tk.StringVar(value=start.strftime("%H:%M") if start else "")
        self.end_date_var = tk.StringVar(value=end.strftime("%Y-%m-%d") if end else "")
        self.end_time_var = tk.StringVar(value=end.strftime("%H:%M") if end else "")
        self.notes_text = None
        self.rows_frame = None
        self.form_canvas = None
        self.form_window = None

        self.build()
        existing_tasks = task_set.tasks if task_set else []
        for item in existing_tasks:
            self.add_task_row(item)
        if not existing_tasks:
            self.add_task_row()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(50, lambda: self.title_entry.focus_set())

    def build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        form_shell = tk.Frame(self, bg=COLORS["bg"])
        form_shell.grid(row=0, column=0, sticky="nsew")
        form_shell.grid_rowconfigure(0, weight=1)
        form_shell.grid_columnconfigure(0, weight=1)

        self.form_canvas = tk.Canvas(form_shell, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_shell, orient="vertical", command=self.form_canvas.yview)
        self.form_canvas.configure(yscrollcommand=scrollbar.set)
        self.form_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        form_frame = tk.Frame(self.form_canvas, bg=COLORS["bg"])
        self.form_window = self.form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_frame.bind("<Configure>", lambda _event: self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all")))
        self.form_canvas.bind("<Configure>", self.resize_form_canvas)
        self.form_canvas.bind("<MouseWheel>", self.scroll_form)

        shell = RoundedFrame(form_frame, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=24, pady=22)
        shell.pack(fill="both", expand=True, padx=16, pady=16)
        body = shell.content
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=1)
        body.grid_columnconfigure(3, weight=0)

        tk.Label(
            body,
            text="New task set" if self.task_set is None else "Edit task set",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 18))

        self.title_entry = self.field(body, "Task set name", self.title_var, 1, columnspan=4, width=82)
        self.date_field(body, "Start date", self.start_date_var, 3, 0)
        self.time_field(body, "Start time", self.start_time_var, 3, 1)
        self.date_field(body, "End date", self.end_date_var, 3, 2)
        self.time_field(body, "End time", self.end_time_var, 3, 3)

        tk.Label(body, text="Tasks", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).grid(
            row=5, column=0, sticky="w", pady=(18, 8)
        )
        self.rows_frame = tk.Frame(body, bg=COLORS["surface"])
        self.rows_frame.grid(row=6, column=0, columnspan=4, sticky="ew")

        self.text_button(body, "Add task", self.add_task_row, secondary=True).grid(row=7, column=0, sticky="w", pady=(12, 0))

        tk.Label(body, text="Notes", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=8, column=0, sticky="w", pady=(14, 4)
        )
        self.notes_text = RoundedText(body, height=3, width=60, radius=8)
        self.notes_text.grid(row=9, column=0, columnspan=4, sticky="ew")
        if self.task_set:
            self.notes_text.insert("1.0", self.task_set.notes)

        footer = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=14)
        footer.grid(row=1, column=0, sticky="ew")
        actions = tk.Frame(footer, bg=COLORS["bg"])
        actions.pack(side="right")
        self.text_button(actions, "Cancel", self.destroy, secondary=True).pack(side="left", padx=(0, 8))
        self.text_button(actions, "Save", self.submit).pack(side="left")
        self.bind_scroll_events(form_frame)

    def resize_form_canvas(self, event):
        self.form_canvas.itemconfigure(self.form_window, width=event.width)

    def scroll_form(self, event):
        self.form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_scroll_events(self, widget):
        widget.bind("<MouseWheel>", self.scroll_form, add="+")
        for child in widget.winfo_children():
            self.bind_scroll_events(child)

    def field(self, parent, label, variable, row, column=0, columnspan=1, width=18):
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=column, columnspan=columnspan, sticky="w", pady=(0, 4), padx=(0 if column == 0 else 10, 0)
        )
        entry = RoundedEntry(parent, textvariable=variable, width=max(90, width * 9), radius=8)
        entry.grid(
            row=row + 1,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=(0 if column == 0 else 10, 0),
        )
        return entry

    def date_field(self, parent, label, variable, row, column):
        frame = tk.Frame(parent, bg=COLORS["surface"])
        frame.grid(row=row + 1, column=column, sticky="w", padx=(0 if column == 0 else 18, 0))
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=column, sticky="w", pady=(14, 4), padx=(0 if column == 0 else 18, 0)
        )
        RoundedEntry(frame, textvariable=variable, width=150, radius=8, placeholder="YYYY-MM-DD").pack(side="left")
        RoundedButton(
            frame,
            "Cal",
            lambda var=variable: self.pick_date(var),
            COLORS["surface_2"],
            COLORS["text"],
            activebackground=COLORS["line"],
            width=42,
            height=38,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(6, 0))

    def time_field(self, parent, label, variable, row, column):
        tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=column, sticky="w", pady=(14, 4), padx=(18, 0)
        )
        times = tuple(f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30))
        ttk.Combobox(parent, textvariable=variable, values=times, width=9).grid(
            row=row + 1, column=column, sticky="w", padx=(18, 0)
        )

    def pick_date(self, variable):
        dialog = DatePickerDialog(self, variable.get())
        self.wait_window(dialog)
        if dialog.result:
            variable.set(dialog.result)

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
            padx=16,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            radius=8,
        )

    def add_task_row(self, item=None):
        row_index = len(self.task_rows)
        row = tk.Frame(self.rows_frame, bg=COLORS["surface"])
        row.grid(row=row_index, column=0, sticky="ew", pady=(0, 8))
        title_var = tk.StringVar(value=item.title if item else "")
        category_var = tk.StringVar(value=item.category if item else "Learning")
        default_unit, default_total = category_defaults(category_var.get())
        total_var = tk.StringVar(value=str(item.total_units if item else default_total))
        completed_var = tk.StringVar(value=str(item.completed_units if item else 0))
        unit_var = tk.StringVar(value=item.unit_name if item else default_unit)
        notes_var = tk.StringVar(value=item.notes if item else "")

        RoundedEntry(row, title_var, width=180, radius=8, placeholder="Task").pack(side="left")
        ttk.Combobox(
            row,
            textvariable=category_var,
            values=("Learning", "Series", "Movies", "Reading", "Custom"),
            state="readonly",
            width=10,
        ).pack(side="left", padx=(8, 0))
        RoundedEntry(row, total_var, width=58, radius=8, placeholder="Total").pack(side="left", padx=(8, 0))
        RoundedEntry(row, completed_var, width=76, radius=8, placeholder="Done").pack(side="left", padx=(8, 0))
        RoundedEntry(row, unit_var, width=90, radius=8, placeholder="Unit").pack(side="left", padx=(8, 0))
        RoundedEntry(row, notes_var, width=130, radius=8, placeholder="Notes").pack(side="left", padx=(8, 0))
        RoundedButton(
            row,
            "X",
            lambda frame=row: self.remove_task_row(frame),
            COLORS["surface_2"],
            COLORS["danger"],
            activebackground=COLORS["line"],
            width=34,
            height=38,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(8, 0))

        def apply_defaults(*_args):
            unit_name, total_units = category_defaults(category_var.get())
            if not unit_var.get().strip():
                unit_var.set(unit_name)
            if not total_var.get().strip():
                total_var.set(str(total_units))

        category_var.trace_add("write", apply_defaults)
        self.task_rows.append(
            {
                "frame": row,
                "id": item.id if item else str(uuid.uuid4()),
                "title": title_var,
                "category": category_var,
                "total": total_var,
                "completed": completed_var,
                "unit": unit_var,
                "notes": notes_var,
            }
        )
        self.bind_scroll_events(row)

    def remove_task_row(self, frame):
        self.task_rows = [row for row in self.task_rows if row["frame"] != frame]
        frame.destroy()

    def submit(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Please enter a task set name.")
            return
        try:
            start_at = parse_date_time(self.start_date_var.get(), self.start_time_var.get(), "00:00")
            end_at = parse_date_time(self.end_date_var.get(), self.end_time_var.get(), "23:59")
        except ValueError as error:
            messagebox.showerror("Invalid range", str(error))
            return
        if start_at and end_at and parse_iso_datetime(end_at) <= parse_iso_datetime(start_at):
            messagebox.showerror("Invalid range", "End date and time must be after the start.")
            return

        tasks = []
        try:
            for row in self.task_rows:
                task_title = row["title"].get().strip()
                if not task_title:
                    continue
                total_units = max(1, int(row["total"].get()))
                completed_units = min(total_units, max(0, int(row["completed"].get() or 0)))
                tasks.append(
                    TaskSetTask(
                        id=row["id"],
                        title=task_title,
                        category=row["category"].get(),
                        total_units=total_units,
                        completed_units=completed_units,
                        unit_name=row["unit"].get().strip() or "steps",
                        notes=row["notes"].get().strip(),
                    )
                )
        except ValueError:
            messagebox.showerror("Invalid tasks", "Task totals and completed values must be whole numbers.")
            return
        if not tasks:
            messagebox.showerror("Missing tasks", "Add at least one task to this set.")
            return

        self.result = {
            "title": title,
            "start_at": start_at,
            "end_at": end_at,
            "tasks": tasks,
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
        self.selected_task_set_id = None
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

        primary_filters = (CURRENT_FILTER, TASKSETS_FILTER, WATCHLIST_FILTER, "Movies", "Series")
        secondary_filters = ("Learning", "Reading", "Custom")
        utility_filters = ("Complete",)

        self.sidebar_label(sidebar, "Focus").pack(anchor="w", pady=(0, 10))

        for label in primary_filters:
            button = self.filter_button(sidebar, label)
            button.pack(fill="x", pady=(0, 8))

        tk.Frame(sidebar, bg=COLORS["line"], height=1).pack(fill="x", pady=(6, 12))

        self.sidebar_label(sidebar, "Projects").pack(anchor="w", pady=(0, 10))

        for label in secondary_filters:
            button = self.filter_button(sidebar, label)
            button.pack(fill="x", pady=(0, 8))

        tk.Frame(sidebar, bg=COLORS["surface"], height=8).pack(fill="x", expand=True)

        self.sidebar_label(sidebar, "History").pack(anchor="w", pady=(0, 10))

        for label in utility_filters:
            button = self.filter_button(sidebar, label)
            button.pack(fill="x")

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

    def filter_button(self, parent, label):
        button = RoundedButton(
            parent,
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
        setattr(self, f"filter_{label}", button)
        return button

    def sidebar_label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
        )

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
        if value != TASKSETS_FILTER:
            self.selected_task_set_id = None
        self.render()

    def open_settings(self):
        dialog = SettingsDialog(self)
        self.wait_window(dialog)

    def open_add_dialog(self):
        if self.filter_var.get() == TASKSETS_FILTER:
            self.open_task_set_dialog()
            return
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

    def open_task_set_dialog(self, task_set=None):
        dialog = TaskSetDialog(self, task_set)
        self.wait_window(dialog)
        if not dialog.result:
            return
        if task_set:
            for key, value in dialog.result.items():
                setattr(task_set, key, value)
            self.store.save()
        else:
            task_set = TaskSet(id=str(uuid.uuid4()), created_at=now_iso(), **dialog.result)
            self.store.add_task_set(task_set)
            self.selected_task_set_id = task_set.id
        self.filter_var.set(TASKSETS_FILTER)
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

    def filtered_task_sets(self):
        query = self.search_var.get().strip().lower()
        task_sets = self.store.task_sets
        if query:
            task_sets = [
                task_set
                for task_set in task_sets
                if query in task_set.title.lower()
                or query in task_set.notes.lower()
                or any(query in task.title.lower() or query in task.notes.lower() for task in task_set.tasks)
            ]
        return task_sets

    def render(self):
        self.update_filter_buttons()
        self.render_stats()
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.cards.clear()

        if self.filter_var.get() == TASKSETS_FILTER:
            self.render_task_sets()
            return

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

    def render_task_sets(self):
        if self.selected_task_set_id:
            task_set = self.store.get_task_set(self.selected_task_set_id)
            if task_set:
                self.render_task_set_detail(task_set)
                return
            self.selected_task_set_id = None

        task_sets = self.filtered_task_sets()
        if not task_sets:
            self.render_empty_task_sets()
            return
        columns = 2 if self.winfo_width() >= 940 else 1
        for index, task_set in enumerate(task_sets):
            card = self.task_set_card(self.list_frame, task_set)
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=(0, 14), pady=(0, 14))
            self.list_frame.grid_columnconfigure(index % columns, weight=1)

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
        task_sets = len(self.store.task_sets)
        values = (
            f"{total} current item{'s' if total != 1 else ''}",
            f"{task_sets} task set{'s' if task_sets != 1 else ''}",
            f"{to_watch} to watch",
            f"{complete} complete, {running} timer{'s' if running != 1 else ''}",
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

    def render_empty_task_sets(self):
        empty = tk.Frame(self.list_frame, bg=COLORS["bg"], pady=80)
        empty.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            empty,
            text="No task sets yet",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack()
        tk.Label(
            empty,
            text="Create a set for a deadline, weekend plan, or longer project range.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(pady=(6, 18))
        self.text_button(empty, "Add task set", self.open_task_set_dialog).pack()

    def task_set_card(self, parent, task_set):
        card = RoundedFrame(parent, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=18, pady=16)
        body = card.content
        body.grid_columnconfigure(0, weight=1)

        top = tk.Frame(body, bg=COLORS["surface"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        tk.Label(
            top,
            text=task_set.title,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            wraplength=340,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        RoundedLabel(
            top,
            text=f"{task_set.complete_count()}/{len(task_set.tasks)} tasks",
            bg=COLORS["accent_2"],
            fg=COLORS["accent"],
            padx=9,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            radius=8,
        ).grid(row=0, column=1, sticky="e")

        self.progress_line(body, 1, "Tasks", task_set.task_progress())
        self.progress_line(body, 2, "Time", task_set.time_progress())

        tk.Label(
            body,
            text=task_set.range_label(),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=420,
        ).grid(row=3, column=0, sticky="ew", pady=(8, 12))

        actions = tk.Frame(body, bg=COLORS["surface"])
        actions.grid(row=4, column=0, sticky="ew")
        self.small_button(actions, "Open", lambda tid=task_set.id: self.open_task_set_detail(tid), accent=True).pack(side="left")
        self.small_button(actions, "Edit", lambda item=task_set: self.open_task_set_dialog(item)).pack(side="right", padx=(6, 0))
        self.small_button(actions, "Delete", lambda tid=task_set.id: self.delete_task_set(tid), danger=True).pack(side="right")
        return card

    def progress_line(self, parent, row, label, value):
        frame = tk.Frame(parent, bg=COLORS["surface"])
        frame.grid(row=row, column=0, sticky="ew", pady=(14 if row == 1 else 8, 0))
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(frame, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"), width=7, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        progress = ttk.Progressbar(
            frame,
            style="Completed.Horizontal.TProgressbar" if value == 1 else "Horizontal.TProgressbar",
            maximum=100,
            value=(value or 0) * 100,
        )
        progress.grid(row=0, column=1, sticky="ew")
        tk.Label(
            frame,
            text=format_percent(value),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
            width=8,
            anchor="e",
        ).grid(row=0, column=2, padx=(10, 0))

    def open_task_set_detail(self, task_set_id):
        self.selected_task_set_id = task_set_id
        self.filter_var.set(TASKSETS_FILTER)
        self.render()

    def render_task_set_detail(self, task_set):
        header = tk.Frame(self.list_frame, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)
        self.small_button(header, "< Back", self.close_task_set_detail).grid(row=0, column=0, sticky="w")
        self.small_button(header, "Edit set", lambda item=task_set: self.open_task_set_dialog(item)).grid(row=0, column=1, padx=(8, 0))
        self.small_button(header, "Delete set", lambda tid=task_set.id: self.delete_task_set(tid), danger=True).grid(row=0, column=2, padx=(8, 0))

        summary = RoundedFrame(
            self.list_frame,
            bg=COLORS["surface"],
            parent_bg=COLORS["bg"],
            border=COLORS["line"],
            radius=8,
            padx=20,
            pady=18,
        )
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        body = summary.content
        body.grid_columnconfigure(0, weight=1)
        tk.Label(
            body,
            text=task_set.title,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
            justify="left",
            wraplength=760,
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            body,
            text=task_set.range_label(),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.progress_line(body, 2, "Tasks", task_set.task_progress())
        self.progress_line(body, 3, "Time", task_set.time_progress())
        if task_set.notes:
            tk.Label(
                body,
                text=task_set.notes,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="w",
                justify="left",
                wraplength=760,
            ).grid(row=4, column=0, sticky="ew", pady=(12, 0))

        for index, task in enumerate(task_set.tasks, start=2):
            card = self.task_set_task_card(self.list_frame, task_set, task)
            card.grid(row=index, column=0, sticky="ew", pady=(0, 12))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def close_task_set_detail(self):
        self.selected_task_set_id = None
        self.render()

    def task_set_task_card(self, parent, task_set, task):
        card = RoundedFrame(parent, bg=COLORS["surface"], parent_bg=COLORS["bg"], border=COLORS["line"], radius=8, padx=18, pady=15)
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
            font=("Segoe UI", 13, "bold"),
            anchor="w",
            justify="left",
            wraplength=640,
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
        self.progress_line(body, 1, f"{task.completed_units}/{task.total_units}", task.progress())
        if task.notes:
            tk.Label(
                body,
                text=task.notes,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
                wraplength=720,
                justify="left",
                anchor="w",
            ).grid(row=2, column=0, sticky="ew", pady=(8, 0))
        actions = tk.Frame(body, bg=COLORS["surface"])
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        if task.total_units > 1:
            self.small_button(actions, "-1", lambda sid=task_set.id, tid=task.id: self.bump_task_set_task(sid, tid, -1)).pack(side="left")
            self.small_button(actions, "+1", lambda sid=task_set.id, tid=task.id: self.bump_task_set_task(sid, tid, 1)).pack(
                side="left", padx=(6, 0)
            )
        if not task.is_complete():
            self.small_button(actions, "Complete", lambda sid=task_set.id, tid=task.id: self.complete_task_set_task(sid, tid), accent=True).pack(
                side="left", padx=(6, 0)
            )
        return card

    def bump_task_set_task(self, task_set_id, task_id, amount):
        task_set = self.store.get_task_set(task_set_id)
        if not task_set:
            return
        task = next((item for item in task_set.tasks if item.id == task_id), None)
        if not task:
            return
        task.completed_units = max(0, min(task.total_units, task.completed_units + amount))
        self.store.save()
        self.render()

    def complete_task_set_task(self, task_set_id, task_id):
        task_set = self.store.get_task_set(task_set_id)
        if not task_set:
            return
        task = next((item for item in task_set.tasks if item.id == task_id), None)
        if not task:
            return
        task.completed_units = task.total_units
        self.store.save()
        self.render()

    def delete_task_set(self, task_set_id):
        task_set = self.store.get_task_set(task_set_id)
        if not task_set:
            return
        confirmed = messagebox.askyesno("Delete task set", f"Delete '{task_set.title}'?")
        if not confirmed:
            return
        self.store.delete_task_set(task_set_id)
        if self.selected_task_set_id == task_set_id:
            self.selected_task_set_id = None
        self.render()

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
