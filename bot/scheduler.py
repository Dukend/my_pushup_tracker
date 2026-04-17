"""
scheduler.py — background loop that fires reminders at configured times.

Runs as an asyncio task. Wakes every 30 s, checks current HH:MM against
each enabled reminder, sends once per day per reminder.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from bot.config import Settings
from bot.formatters import progress_bar
from bot.storage import Storage
from bot.todo import TodoStorage

log = logging.getLogger(__name__)

# Reminder types that get special rich content
BUILTIN_TEMPLATES = {"morning", "evening", "summary"}


async def reminder_loop(bot: Bot, storage: Storage, cfg: Settings) -> None:
    sent: dict[str, str] = {}  # reminder_key → last-sent date string
    todo = TodoStorage(cfg.data_file)
    last_archive_date: str = ""

    while True:
        await asyncio.sleep(30)
        try:
            now = datetime.now(cfg.timezone)
            hhmm = now.strftime("%H:%M")
            date_str = now.date().isoformat()

            # ── Midnight archive: move completed todos to archive ─────────────
            if hhmm == "00:01" and last_archive_date != date_str:
                last_archive_date = date_str
                n = todo.archive_done(cfg.timezone)
                if n:
                    log.info("Archived %d completed todo(s)", n)

            reminders = storage.get_reminders()
            goal = storage.get_goal()

            for key, r in reminders.items():
                if not r.get("enabled", True):
                    continue
                if r.get("time") != hhmm:
                    continue
                sent_key = f"{key}:{date_str}"
                if sent_key in sent:
                    continue

                sent[sent_key] = date_str

                text = _build_message(key, r, storage, todo, cfg, goal, now)
                if text and cfg.allowed_user_id:
                    await bot.send_message(cfg.allowed_user_id, text, parse_mode="HTML")
                    log.info("Sent reminder '%s' (%s)", key, r.get("label", key))

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error("Reminder loop error: %s", exc)


def _build_message(
    key: str,
    r: dict,
    storage: Storage,
    todo: TodoStorage,
    cfg: Settings,
    goal: int,
    now: datetime,
) -> str | None:
    label = r.get("label", key)

    # ── Утреннее ──────────────────────────────────────────────────────────────
    if key == "morning":
        yesterday = (now.date() - timedelta(days=1)).isoformat()
        y_val = storage._load()["days"].get(yesterday, 0)  # noqa: SLF001
        streak = storage.calc_streak(cfg.timezone)
        active = todo.get_active()

        text = (
            f"🌅 <b>Доброе утро!</b>\n\n"
            f"Цель сегодня: <b>{goal}</b> отжиманий\n"
            f"Вчера:        <b>{y_val}</b>\n"
            f"🔥 Стрик:     <b>{streak}</b> дн."
        )
        if active:
            lines = "\n".join(
                f"  {'🔴' if t['priority'] == 'high' else '⚪'} {t['text']}"
                for t in active[:10]
            )
            text += f"\n\n📋 <b>Задачи на сегодня ({len(active)}):</b>\n{lines}"
            if len(active) > 10:
                text += f"\n  <i>…и ещё {len(active) - 10}</i>"
        return text

    # ── Вечернее (только если цель не выполнена) ─────────────────────────────
    if key == "evening":
        today_val = storage.get_today(cfg.timezone)
        if today_val >= goal:
            return None
        left = goal - today_val
        text = (
            f"💪 <b>Не забудь про отжимания!</b>\n\n"
            f"Сделано: <b>{today_val}</b> / {goal}  (осталось <b>{left}</b>)\n\n"
            f"{progress_bar(today_val, goal)}"
        )
        # Add active tasks reminder if any
        active = todo.get_active()
        if active:
            high = [t for t in active if t["priority"] == "high"]
            if high:
                lines = "\n".join(f"  🔴 {t['text']}" for t in high[:5])
                text += f"\n\n⚠️ <b>Важные задачи ({len(high)}):</b>\n{lines}"
        return text

    # ── Итог дня ─────────────────────────────────────────────────────────────
    if key == "summary":
        today_val = storage.get_today(cfg.timezone)
        total = storage.get_total()
        streak = storage.calc_streak(cfg.timezone)
        done = today_val >= goal
        s = todo.stats(cfg.timezone)

        text = (
            f"{'🎯' if done else '📋'} <b>Итог дня</b>\n\n"
            f"Сегодня: <b>{today_val}</b> / {goal}  {'✅' if done else '❌'}\n"
            f"Всего:   <b>{total}</b>\n"
            f"🔥 Стрик: <b>{streak}</b> дн.\n\n"
            f"{progress_bar(today_val, goal)}"
        )
        if s["done_today"] or s["active"]:
            text += (
                f"\n\n📋 <b>Задачи:</b> "
                f"выполнено <b>{s['done_today']}</b>  |  "
                f"осталось <b>{s['active']}</b>"
            )
        return text

    # ── Кастомное напоминание ─────────────────────────────────────────────────
    today_val = storage.get_today(cfg.timezone)
    active = todo.get_active()
    text = (
        f"⏰ <b>{label}</b>\n\n"
        f"Сегодня: <b>{today_val}</b> / {goal}\n"
        f"{progress_bar(today_val, goal)}"
    )
    if active:
        lines = "\n".join(
            f"  {'🔴' if t['priority'] == 'high' else '⚪'} {t['text']}"
            for t in active[:5]
        )
        text += f"\n\n📋 <b>Активных задач: {len(active)}</b>\n{lines}"
    return text
