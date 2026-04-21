"""
handlers/commands.py — slash-command handlers.
Storage is injected via aiogram DI (dp["storage"]).
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.formatters import fmt_add, fmt_history, fmt_stats, progress_bar
from bot.keyboards import back_to_menu, main_menu
from bot.storage import Storage

router = Router()


def guard(msg: Message) -> bool:
    return settings.allowed(msg.from_user.id)


# ── /start  /help  /menu ──────────────────────────────────────────────────────


@router.message(Command("start", "help", "menu"))
async def cmd_start(msg: Message):
    if not guard(msg):
        return
    await msg.answer(
        "💪 <b>Push-up Tracker</b>\n\n"
        "Записывай отжимания, следи за прогрессом и не пропускай тренировки.\n\n"
        "<b>Быстрый старт:</b>\n"
        "• Напиши число — сразу запишется: <code>30</code>\n"
        "• /add 30 — то же самое\n"
        "• /stats — вся статистика\n"
        "• /goal 100 — установить дневную цель\n"
        "• /remind — управление напоминаниями\n\n"
        "Или используй меню 👇",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ── /add ──────────────────────────────────────────────────────────────────────


@router.message(Command("add"))
async def cmd_add(msg: Message, storage: Storage):
    if not guard(msg):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await msg.answer("Использование: /add 30", reply_markup=back_to_menu())
        return
    await _do_add(msg, storage, int(parts[1].strip()))


@router.message(F.text.regexp(r"^\d+$"))
async def msg_number(msg: Message, storage: Storage):
    if not guard(msg):
        return
    await _do_add(msg, storage, int(msg.text))


async def _do_add(msg: Message, storage: Storage, n: int):
    if not (1 <= n <= 10_000):
        await msg.answer("Число должно быть от 1 до 10 000.")
        return
    goal = storage.get_goal()
    prev = storage.get_today(settings.timezone)
    today_val, total_val, new_record = storage.add(n, settings.timezone)
    just_reached = today_val >= goal and prev < goal
    await msg.answer(
        fmt_add(n, today_val, total_val, goal, new_record, just_reached),
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


# ── /today  /total  /stats  /history  /record  /undo ─────────────────────────


@router.message(Command("today"))
async def cmd_today(msg: Message, storage: Storage):
    if not guard(msg):
        return
    today = storage.get_today(settings.timezone)
    goal = storage.get_goal()
    await msg.answer(
        f"📅 Сегодня: <b>{today}</b> / {goal}\n{progress_bar(today, goal)}",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


@router.message(Command("total"))
async def cmd_total(msg: Message, storage: Storage):
    if not guard(msg):
        return
    await msg.answer(
        f"🏋 Всего за всё время: <b>{storage.get_total()}</b>",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


@router.message(Command("stats"))
async def cmd_stats(msg: Message, storage: Storage):
    if not guard(msg):
        return
    await msg.answer(
        fmt_stats(
            today=storage.get_today(settings.timezone),
            total=storage.get_total(),
            goal=storage.get_goal(),
            streak=storage.calc_streak(settings.timezone),
            record=storage.get_record(),
        ),
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


@router.message(Command("history"))
async def cmd_history(msg: Message, storage: Storage):
    if not guard(msg):
        return
    await msg.answer(
        fmt_history(storage.get_history(settings.timezone), storage.get_goal()),
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


@router.message(Command("record"))
async def cmd_record(msg: Message, storage: Storage):
    if not guard(msg):
        return
    await msg.answer(
        f"🏆 Рекорд за день: <b>{storage.get_record()}</b>",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


@router.message(Command("undo"))
async def cmd_undo(msg: Message, storage: Storage):
    if not guard(msg):
        return
    ok, n = storage.undo()
    await msg.answer(
        f"↩️ Отменено: −{n} отжиманий" if ok else "Нечего отменять.",
        reply_markup=back_to_menu(),
    )


# ── /goal ─────────────────────────────────────────────────────────────────────


@router.message(Command("goal"))
async def cmd_goal(msg: Message, storage: Storage):
    if not guard(msg):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 1:
        goal = storage.get_goal()
        today = storage.get_today(settings.timezone)
        await msg.answer(
            f"🎯 Цель: <b>{goal}</b> отжиманий в день\n"
            f"Сегодня: <b>{today}</b>\n\n"
            f"{progress_bar(today, goal)}\n\n"
            f"<i>Изменить: /goal 150</i>",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return
    if not parts[1].strip().isdigit():
        await msg.answer("Использование: /goal 150")
        return
    n = int(parts[1].strip())
    if not (1 <= n <= 100_000):
        await msg.answer("Цель: от 1 до 100 000.")
        return
    storage.set_goal(n)
    await msg.answer(
        f"🎯 Новая цель: <b>{n}</b> отжиманий в день",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
