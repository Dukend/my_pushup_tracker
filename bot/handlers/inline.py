"""
handlers/inline.py — all InlineKeyboard callback_query handlers.\
Storage is injected via aiogram DI (dp["storage"]).
"""

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.formatters import fmt_add, fmt_history, fmt_stats, progress_bar
from bot.keyboards import back_to_menu, main_menu, reminders_menu
from bot.storage import Storage

router = Router()
storage = Storage(settings.data_file)


def guard(cq: CallbackQuery) -> bool:
    return settings.allowed(cq.from_user.id)


async def _answer(cq: CallbackQuery, text: str, keyboard=None):
    """Edit the message or send a new one if edit fails."""
    kb = keyboard or back_to_menu()
    try:
        await cq.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cq.answer()


# ── Menu navigation ───────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "main_menu")
async def cb_main_menu(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(
        cq,
        "💪 <b>Pushup Tracker</b>\nВыбери действие:",
        main_menu(),
    )


# ── Stats & info ──────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "today")
async def cb_today(cq: CallbackQuery):
    if not guard(cq):
        return
    today = storage.get_today(settings.timezone)
    goal = storage.get_goal()
    await _answer(
        cq, f"📅 Сегодня: <b>{today}</b> / {goal}\n{progress_bar(today, goal)}"
    )


@router.callback_query(lambda c: c.data == "total")
async def cb_total(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(cq, f"🏋 Всего за всё время: <b>{storage.get_total()}</b>")


@router.callback_query(lambda c: c.data == "stats")
async def cb_stats(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(
        cq,
        fmt_stats(
            today=storage.get_today(settings.timezone),
            total=storage.get_total(),
            goal=storage.get_goal(),
            streak=storage.calc_streak(settings.timezone),
            record=storage.get_record(),
        ),
    )


@router.callback_query(lambda c: c.data == "history")
async def cb_history(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(
        cq,
        fmt_history(storage.get_history(settings.timezone), storage.get_goal()),
    )


@router.callback_query(lambda c: c.data == "goal")
async def cb_goal(cq: CallbackQuery):
    if not guard(cq):
        return
    goal = storage.get_goal()
    today = storage.get_today(settings.timezone)
    await _answer(
        cq,
        f"🎯 Цель: <b>{goal}</b> отжиманий в день\n"
        f"Сегодня: <b>{today}</b>\n\n"
        f"{progress_bar(today, goal)}\n\n"
        f"<i>Изменить через команду: /goal 150</i>",
    )


@router.callback_query(lambda c: c.data == "record")
async def cb_record(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(cq, f"🏆 Рекорд за день: <b>{storage.get_record()}</b>")


# ── Quick add ─────────────────────────────────────────────────────────────────

QUICK_AMOUNTS = {
    "quick_20": 20,
    "quick_30": 30,
    "quick_40": 40,
    "quick_50": 50,
}


@router.callback_query(lambda c: c.data in QUICK_AMOUNTS)
async def cb_quick_add(cq: CallbackQuery):
    if not guard(cq):
        return
    n = QUICK_AMOUNTS[cq.data]
    goal = storage.get_goal()
    prev = storage.get_today(settings.timezone)
    today_val, total_val, new_record = storage.add(n, settings.timezone)
    just_reached = today_val >= goal and prev < goal
    await _answer(cq, fmt_add(n, today_val, total_val, goal, new_record, just_reached))


# ── Undo ──────────────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "undo")
async def cb_undo(cq: CallbackQuery):
    if not guard(cq):
        return
    ok, n = storage.undo()
    await _answer(cq, f"↩️ Отменено: −{n} отжиманий" if ok else "Нечего отменять.")


# ── Reminders list ────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "reminders_list")
async def cb_reminders_list(cq: CallbackQuery):
    if not guard(cq):
        return
    r = storage.get_reminders()
    await _answer(cq, "⏰ <b>Напоминания</b>\nУправляй расписанием:", reminders_menu(r))


@router.callback_query(lambda c: c.data.startswith("rem_toggle_"))
async def cb_rem_toggle(cq: CallbackQuery):
    if not guard(cq):
        return
    key = cq.data.removeprefix("rem_toggle_")
    r = storage.get_reminders()
    current = r.get(key, {}).get("enabled", True)
    storage.toggle_reminder(key, not current)
    r = storage.get_reminders()
    await _answer(cq, "⏰ <b>Напоминания</b>", reminders_menu(r))


@router.callback_query(lambda c: c.data.startswith("rem_delete_"))
async def cb_rem_delete(cq: CallbackQuery):
    if not guard(cq):
        return
    from bot.keyboards import confirm_delete

    key = cq.data.removeprefix("rem_delete_")
    r = storage.get_reminders()
    label = r.get(key, {}).get("label", key)
    await _answer(
        cq,
        f"Удалить напоминание <b>{label}</b>?",
        confirm_delete(key),
    )


@router.callback_query(lambda c: c.data.startswith("rem_confirm_delete_"))
async def cb_rem_confirm_delete(cq: CallbackQuery):
    if not guard(cq):
        return
    key = cq.data.removeprefix("rem_confirm_delete_")
    storage.delete_reminder(key)
    r = storage.get_reminders()
    await _answer(cq, "🗑 Удалено.\n\n⏰ <b>Напоминания</b>", reminders_menu(r))


@router.callback_query(lambda c: c.data == "rem_new")
async def cb_rem_new(cq: CallbackQuery):
    if not guard(cq):
        return
    await _answer(
        cq,
        "➕ <b>Новое напоминание</b>\n\n"
        "Отправь команду в формате:\n"
        "<code>/remind add HH:MM Название</code>\n\n"
        "Пример:\n"
        "<code>/remind add 13:00 Обеденная тренировка</code>",
    )
