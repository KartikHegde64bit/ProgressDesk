import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


APP_DIR = Path.home() / "AppData" / "Local" / "ProgressDesk"
DATA_FILE = APP_DIR / "tasks.json"


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

    def is_running(self):
        return self.timer_started_at is not None

    def sync_completion_state(self):
        if self.is_complete():
            if self.is_running():
                self.spent_seconds = self.current_spent_seconds()
                self.timer_started_at = None
            if not self.completed_at:
                self.completed_at = now_iso()
        else:
            self.completed_at = None


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


def category_defaults(category):
    values = {
        "Learning": ("parts", 5),
        "Series": ("episodes", 10),
        "Movies": ("movies", 1),
        "Reading": ("chapters", 12),
        "Custom": ("steps", 5),
    }
    return values.get(category, values["Custom"])


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

    def delete(self, task_id):
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self.save()

    def get(self, task_id):
        return next((task for task in self.tasks if task.id == task_id), None)


def main():
    store = TaskStore(DATA_FILE)
    print(f"Loaded {len(store.tasks)} task(s) from {DATA_FILE}")


if __name__ == "__main__":
    main()
