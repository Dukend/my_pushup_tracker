"""
handlers/reminders_cmd.py — /remind command with all subcommands.

Usage
-----
/remind                          — show schedule (inline menu)
/remind morning 07:30            — update built-in reminder time
/remind evening 20:00
/remind summary 22:00
/remind on  morning              — enable
/remind off evening              — disable
/remind add HH:MM Label text     — create custom reminder
/remind del <key>                — delete custom reminder
"""

import uuid

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.keyboards import back_to_reminders, reminders_menu
from bot.storage import Storage

router = Router()

BUILTIN_KEYS = {"morning", "evening", "summary"}
BUILTIN_NAMES = {"morning": "Утреннее", "evening": "Вечернее", "summary": "Итог дня"}


def guard(msg: Message) -> bool:
    return settings.allowed(msg.from_user.id)


def _parse_time(s: str) -> tuple[int, int] | None:
    try:
        h, m = s.strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        pass
    return None


@router.message(Command("remind"))
async def cmd_remind(msg: Message, storage: Storage):
    if not guard(msg):
        return

    # strip "/remind" and split the rest
    raw = msg.text or ""
    parts = raw.split(maxsplit=4)  # ["/remind", sub, arg1, arg2, ...]
    sub = parts[1].lower() if len(parts) > 1 else None

    # ── /remind  →  show menu ────────────────────────────────────────────────
    if sub is None:
        r = storage.get_reminders()
        await msg.answer("⏰ <b>Напоминания</b>", parse_mode="HTML", reply_markup=reminders_menu(r))
        return

    # ── /remind on|off <key> ─────────────────────────────────────────────────
    if sub in ("on", "off"):
        if len(parts) < 3:
            await msg.answer("Использование: /remind on morning")
            return
        key = parts[2].lower()
        enabled = sub == "on"
        if not storage.toggle_reminder(key, enabled):
            await msg.answer(f"Напоминание «{key}» не найдено.")
            return
        state = "включено ✅" if enabled else "отключено 🔕"
        r = storage.get_reminders()
        label = r.get(key, {}).get("label", key)
        await msg.answer(
            f"<b>{label}</b> — {state}", parse_mode="HTML", reply_markup=back_to_reminders()
        )
        return

    # ── /remind morning|evening|summary HH:MM  (change time) ────────────────
    if sub in BUILTIN_KEYS:
        if len(parts) < 3:
            await msg.answer(f"Использование: /remind {sub} 07:30")
            return
        t = _parse_time(parts[2])
        if not t:
            await msg.answer("Формат времени: HH:MM  (например 07:30)")
            return
        time_str = f"{t[0]:02d}:{t[1]:02d}"
        storage.set_reminder(sub, time_str, BUILTIN_NAMES[sub])
        await msg.answer(
            f"✅ <b>{BUILTIN_NAMES[sub]}</b>: {time_str}",
            parse_mode="HTML",
            reply_markup=back_to_reminders(),
        )
        return

    # ── /remind add HH:MM Label ──────────────────────────────────────────────
    if sub == "add":
        # parts: ["/remind", "add", "HH:MM", "Label", "words..."]
        if len(parts) < 4:
            await msg.answer(
                "Использование:\n<code>/remind add 13:00 Обеденная тренировка</code>",
                parse_mode="HTML",
            )
            return
        t = _parse_time(parts[2])
        if not t:
            await msg.answer("Формат времени: HH:MM  (например 13:00)")
            return
        label = " ".join(parts[3:]).strip()
        if not label:
            await msg.answer("Укажи название: /remind add 13:00 Обед")
            return
        if len(label) > 64:
            await msg.answer("Название слишком длинное (макс. 64 символа).")
            return

        key = f"custom_{uuid.uuid4().hex[:8]}"
        time_str = f"{t[0]:02d}:{t[1]:02d}"
        storage.set_reminder(key, time_str, label, custom=True)
        r = storage.get_reminders()
        await msg.answer(
            f"➕ Создано: <b>{label}</b> в {time_str}",
            parse_mode="HTML",
            reply_markup=reminders_menu(r),
        )
        return

    # ── /remind del <key> ────────────────────────────────────────────────────
    if sub == "del":
        if len(parts) < 3:
            await msg.answer("Использование: /remind del <key>")
            return
        key = parts[2]
        if not storage.delete_reminder(key):
            await msg.answer("Напоминание не найдено или является встроенным.")
            return
        r = storage.get_reminders()
        await msg.answer("🗑 Удалено.", reply_markup=reminders_menu(r))
        return

    # ── Unknown subcommand ────────────────────────────────────────────────────
    await msg.answer(
        "Доступные подкоманды:\n"
        "/remind             — показать список\n"
        "/remind morning 07:30\n"
        "/remind on morning\n"
        "/remind off morning\n"
        "/remind add 13:00 Название\n"
        "/remind del &lt;key&gt;",
        parse_mode="HTML",
    )
