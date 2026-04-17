"""
Storage — thin wrapper around a single JSON file.

Schema
------
{
  "total":   int,
  "days":    { "YYYY-MM-DD": int, ... },
  "record":  int,
  "history": [ {"date": str, "n": int, "ts": str}, ... ],   // last 50
  "goal":    int,
  "reminders": {
    "morning":  {"time": "07:30", "enabled": true, "label": "Доброе утро"},
    "evening":  {"time": "20:00", "enabled": true, "label": "Вечернее"},
    "summary":  {"time": "22:00", "enabled": true, "label": "Итог дня"},
    // user-defined keys:
    "<id>":     {"time": "HH:MM", "enabled": true, "label": str, "custom": true}
  }
}
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_GOAL = 100

DEFAULT_REMINDERS: dict = {
    "morning": {"time": "07:30", "enabled": True, "label": "Доброе утро"},
    "evening": {"time": "20:00", "enabled": True, "label": "Вечернее"},
    "summary": {"time": "22:00", "enabled": True, "label": "Итог дня"},
}


class Storage:
    def __init__(self, path: Path) -> None:
        self._path = path

    # ── Low-level ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # corrupted or empty file — fall through to defaults
        return {
            "total": 0,
            "days": {},
            "record": 0,
            "history": [],
            "goal": DEFAULT_GOAL,
            "reminders": {k: dict(v) for k, v in DEFAULT_REMINDERS.items()},
        }

    def _save(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _today(tz: ZoneInfo) -> str:
        return datetime.now(tz).date().isoformat()

    # ── Pushups ────────────────────────────────────────────────────────────

    def add(self, n: int, tz: ZoneInfo) -> tuple[int, int, bool]:
        """Add n pushups. Returns (today_total, grand_total, is_new_record)."""
        data = self._load()
        key = self._today(tz)
        data["days"][key] = data["days"].get(key, 0) + n
        data["total"] = data.get("total", 0) + n
        data.setdefault("history", []).append({
            "date": key,
            "n": n,
            "ts": datetime.now().isoformat(),
        })
        data["history"] = data["history"][-50:]
        new_record = data["days"][key] > data.get("record", 0)
        if new_record:
            data["record"] = data["days"][key]
        self._save(data)
        return data["days"][key], data["total"], new_record

    def undo(self) -> tuple[bool, int]:
        """Undo last addition. Returns (success, n_removed)."""
        data = self._load()
        if not data.get("history"):
            return False, 0
        last = data["history"].pop()
        n, key = last["n"], last["date"]
        data["days"][key] = max(0, data["days"].get(key, 0) - n)
        if data["days"][key] == 0:
            del data["days"][key]
        data["total"] = max(0, data.get("total", 0) - n)
        self._save(data)
        return True, n

    def get_today(self, tz: ZoneInfo) -> int:
        return self._load()["days"].get(self._today(tz), 0)

    def get_day(self, day: date) -> int:
        """Return pushup count for an arbitrary date."""
        return self._load()["days"].get(day.isoformat(), 0)

    def get_total(self) -> int:
        return self._load().get("total", 0)

    def get_record(self) -> int:
        return self._load().get("record", 0)

    def get_history(self, tz: ZoneInfo, days: int = 7) -> list[tuple[str, int]]:
        data = self._load()
        today = datetime.now(tz).date()
        return [
            (
                (today - timedelta(days=i)).isoformat(),
                data["days"].get((today - timedelta(days=i)).isoformat(), 0),
            )
            for i in range(days - 1, -1, -1)
        ]

    def calc_streak(self, tz: ZoneInfo) -> int:
        """
        Days in a row where the daily goal was met.
        Today counts only if the goal is already reached;
        otherwise we start counting from yesterday.
        """
        data = self._load()
        days = data.get("days", {})
        goal = data.get("goal", DEFAULT_GOAL)
        today = datetime.now(tz).date()

        # Decide starting point
        current = today if days.get(today.isoformat(), 0) >= goal else today - timedelta(days=1)

        streak = 0
        for _ in range(365):
            if days.get(current.isoformat(), 0) >= goal:
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak

    # ── Goal ───────────────────────────────────────────────────────────────

    def get_goal(self) -> int:
        return self._load().get("goal", DEFAULT_GOAL)

    def set_goal(self, n: int) -> None:
        data = self._load()
        data["goal"] = n
        self._save(data)

    # ── Reminders ──────────────────────────────────────────────────────────

    def get_reminders(self) -> dict:
        data = self._load()
        return data.get("reminders", {k: dict(v) for k, v in DEFAULT_REMINDERS.items()})

    def set_reminder(self, key: str, time: str, label: str, custom: bool = False) -> None:
        data = self._load()
        data.setdefault("reminders", {k: dict(v) for k, v in DEFAULT_REMINDERS.items()})
        data["reminders"][key] = {
            "time": time,
            "enabled": True,
            "label": label,
            **({"custom": True} if custom else {}),
        }
        self._save(data)

    def toggle_reminder(self, key: str, enabled: bool) -> bool:
        """Toggle reminder. Returns False if key not found."""
        data = self._load()
        r = data.get("reminders", {})
        if key not in r:
            return False
        r[key]["enabled"] = enabled
        self._save(data)
        return True

    def delete_reminder(self, key: str) -> bool:
        """Delete a custom reminder. Returns False if built-in or not found."""
        data = self._load()
        r = data.get("reminders", {})
        if key not in r or not r[key].get("custom"):
            return False
        del r[key]
        self._save(data)
        return True
