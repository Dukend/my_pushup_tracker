"""
todo.py — Todo list storage layer.

Schema inside pushups.json:
{
  "todos": {
    "<uuid8>": {
      "id":       str,          # same as key, for convenience
      "text":     str,          # task text
      "priority": "high"|"normal",
      "done":     bool,
      "created":  "ISO datetime",
      "done_at":  "ISO datetime" | null
    },
    ...
  }
}

Completed tasks are kept for the current day (history), then
auto-archived at midnight into "todo_archive": {"YYYY-MM-DD": [...]}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class TodoStorage:
    def __init__(self, path: Path) -> None:
        self._path = path

    # ── Low-level ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # corrupted or empty file — fall through to defaults
        return {}

    def _save(self, data: dict) -> None:
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _todos(self, data: dict) -> dict:
        return data.setdefault("todos", {})

    # ── CRUD ──────────────────────────────────────────────────────────────

    def add(self, text: str, priority: str = "normal") -> dict:
        """Create a new task. Returns the created item."""
        data = self._load()
        tid = uuid.uuid4().hex[:8]
        item = {
            "id": tid,
            "text": text.strip(),
            "priority": priority if priority in ("high", "normal") else "normal",
            "done": False,
            "created": datetime.now().isoformat(timespec="seconds"),
            "done_at": None,
        }
        self._todos(data)[tid] = item
        self._save(data)
        return item

    def complete(self, tid: str) -> bool:
        """Mark task as done. Returns False if not found or already done."""
        data = self._load()
        todos = self._todos(data)
        if tid not in todos or todos[tid]["done"]:
            return False
        todos[tid]["done"] = True
        todos[tid]["done_at"] = datetime.now().isoformat(timespec="seconds")
        self._save(data)
        return True

    def uncomplete(self, tid: str) -> bool:
        """Mark task as not done. Returns False if not found."""
        data = self._load()
        todos = self._todos(data)
        if tid not in todos:
            return False
        todos[tid]["done"] = False
        todos[tid]["done_at"] = None
        self._save(data)
        return True

    def delete(self, tid: str) -> bool:
        """Delete a task permanently. Returns False if not found."""
        data = self._load()
        todos = self._todos(data)
        if tid not in todos:
            return False
        del todos[tid]
        self._save(data)
        return True

    def edit(self, tid: str, text: str) -> bool:
        """Edit task text. Returns False if not found."""
        data = self._load()
        todos = self._todos(data)
        if tid not in todos:
            return False
        todos[tid]["text"] = text.strip()
        self._save(data)
        return True

    def set_priority(self, tid: str, priority: str) -> bool:
        """Change priority. Returns False if not found."""
        data = self._load()
        todos = self._todos(data)
        if tid not in todos or priority not in ("high", "normal"):
            return False
        todos[tid]["priority"] = priority
        self._save(data)
        return True

    # ── Queries ────────────────────────────────────────────────────────────

    def get_active(self) -> list[dict]:
        """Return active (not done) tasks, high priority first."""
        todos = self._todos(self._load())
        items = [t for t in todos.values() if not t["done"]]
        return sorted(items, key=lambda t: (t["priority"] != "high", t["created"]))

    def get_done_today(self, tz: ZoneInfo) -> list[dict]:
        """Return tasks completed today."""
        today = datetime.now(tz).date().isoformat()
        todos = self._todos(self._load())
        return [
            t
            for t in todos.values()
            if t["done"] and t.get("done_at", "")[:10] == today
        ]

    def get_all(self) -> list[dict]:
        """Return all tasks (active + done), high priority first."""
        todos = self._todos(self._load())
        return sorted(
            todos.values(),
            key=lambda t: (t["done"], t["priority"] != "high", t["created"]),
        )

    def stats(self, tz: ZoneInfo) -> dict:
        """Return quick stats dict."""
        active = self.get_active()
        done_today = self.get_done_today(tz)
        return {
            "active": len(active),
            "done_today": len(done_today),
            "high": sum(1 for t in active if t["priority"] == "high"),
        }

    # ── Archive ────────────────────────────────────────────────────────────

    def archive_done(self, tz: ZoneInfo) -> int:
        """
        Move all completed tasks to archive keyed by done_at date.
        Called at midnight. Returns count of archived tasks.
        """
        data = self._load()
        todos = self._todos(data)
        to_archive = {k: v for k, v in todos.items() if v["done"]}
        if not to_archive:
            return 0

        archive = data.setdefault("todo_archive", {})
        for item in to_archive.values():
            day = (item.get("done_at") or item["created"])[:10]
            archive.setdefault(day, []).append(item)
            del todos[item["id"]]

        self._save(data)
        return len(to_archive)
