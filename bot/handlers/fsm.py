"""
handlers/fsm.py — FSM dialogs for multi-step input.

Flows
-----
AddTodo:
  1. Bot asks task text
  2. Bot asks priority (inline buttons)
  → task created

AddReminder:
  1. Bot asks time (HH:MM)
  2. Bot asks label
  → reminder created
"""

import uuid

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.storage import Storage
from bot.todo import TodoStorage

router = Router()


# ── State groups ──────────────────────────────────────────────────────────────


class AddTodo(StatesGroup):
    waiting_text = State()
    waiting_priority = State()


class AddReminder(StatesGroup):
    waiting_time = State()
    waiting_label = State()


# ── Keyboards ─────────────────────────────────────────────────────────────────


def priority_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Важная", callback_data="fsm_pri_high"),
                InlineKeyboardButton(text="⚪ Обычная", callback_data="fsm_pri_normal"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="fsm_cancel"),
            ],
        ]
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="fsm_cancel"),
            ]
        ]
    )


# ── Guards ────────────────────────────────────────────────────────────────────


def guard_msg(msg: Message) -> bool:
    return settings.allowed(msg.from_user.id)


def guard_cb(cq: CallbackQuery) -> bool:
    return settings.allowed(cq.from_user.id)


# ══ AddTodo flow ══════════════════════════════════════════════════════════════


@router.callback_query(lambda c: c.data == "todo_new_fsm")
async def fsm_todo_start_cb(cq: CallbackQuery, state: FSMContext):
    """Entry from inline button."""
    if not guard_cb(cq):
        return
    await state.set_state(AddTodo.waiting_text)
    await cq.message.answer(
        "📝 <b>Новая задача</b>\n\nВведи текст задачи:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await cq.answer()


@router.message(Command("new"))
async def fsm_todo_start_cmd(msg: Message, state: FSMContext):
    """Entry from /new command."""
    if not guard_msg(msg):
        return
    await state.set_state(AddTodo.waiting_text)
    await msg.answer(
        "📝 <b>Новая задача</b>\n\nВведи текст задачи:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AddTodo.waiting_text)
async def fsm_todo_got_text(msg: Message, state: FSMContext):
    if not guard_msg(msg):
        return
    text = (msg.text or "").strip()
    if not text:
        await msg.answer("Текст не может быть пустым. Попробуй ещё раз:")
        return
    if len(text) > 200:
        await msg.answer("Слишком длинный текст (макс. 200 символов). Попробуй ещё раз:")
        return
    await state.update_data(text=text)
    await state.set_state(AddTodo.waiting_priority)
    await msg.answer(
        f"Задача: <b>{text}</b>\n\nВыбери приоритет:",
        parse_mode="HTML",
        reply_markup=priority_kb(),
    )


@router.callback_query(lambda c: c.data in ("fsm_pri_high", "fsm_pri_normal"))
async def fsm_todo_got_priority(cq: CallbackQuery, state: FSMContext, todo: TodoStorage):
    if not guard_cb(cq):
        return
    if await state.get_state() != AddTodo.waiting_priority:
        await cq.answer()
        return
    data = await state.get_data()
    priority = "high" if cq.data == "fsm_pri_high" else "normal"
    item = todo.add(data["text"], priority)
    await state.clear()
    pri_label = "🔴 Важная" if priority == "high" else "⚪ Обычная"
    await cq.message.edit_text(
        f"✅ Добавлено: <b>{item['text']}</b>\n{pri_label}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 Список задач", callback_data="todo_list"),
                    InlineKeyboardButton(text="➕ Ещё", callback_data="todo_new_fsm"),
                ]
            ]
        ),
    )
    await cq.answer("✅ Задача добавлена!")


# ══ AddReminder flow ══════════════════════════════════════════════════════════


@router.callback_query(lambda c: c.data == "rem_new_fsm")
async def fsm_remind_start_cb(cq: CallbackQuery, state: FSMContext):
    """Entry from inline button."""
    if not guard_cb(cq):
        return
    await state.set_state(AddReminder.waiting_time)
    await cq.message.answer(
        "⏰ <b>Новое напоминание</b>\n\nВведи время в формате <code>HH:MM</code>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await cq.answer()


@router.message(AddReminder.waiting_time)
async def fsm_remind_got_time(msg: Message, state: FSMContext):
    if not guard_msg(msg):
        return
    raw = (msg.text or "").strip()
    try:
        h, m = raw.split(":")
        h, m = int(h), int(m)
        assert 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        await msg.answer(
            "Неверный формат. Введи время как <code>HH:MM</code>, например <code>13:00</code>:",
            parse_mode="HTML",
        )
        return
    time_str = f"{h:02d}:{m:02d}"
    await state.update_data(time=time_str)
    await state.set_state(AddReminder.waiting_label)
    await msg.answer(
        f"Время: <b>{time_str}</b>\n\nТеперь введи название напоминания:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AddReminder.waiting_label)
async def fsm_remind_got_label(msg: Message, state: FSMContext, storage: Storage):
    if not guard_msg(msg):
        return
    label = (msg.text or "").strip()
    if not label:
        await msg.answer("Название не может быть пустым. Попробуй ещё раз:")
        return
    if len(label) > 64:
        await msg.answer("Слишком длинное название (макс. 64 символа). Попробуй ещё раз:")
        return
    data = await state.get_data()
    key = f"custom_{uuid.uuid4().hex[:8]}"
    time_str = data["time"]
    storage.set_reminder(key, time_str, label, custom=True)
    await state.clear()
    from bot.keyboards import reminders_menu

    await msg.answer(
        f"✅ Создано: <b>{label}</b> в {time_str}",
        parse_mode="HTML",
        reply_markup=reminders_menu(storage.get_reminders()),
    )


# ── Cancel (works in any FSM state) ──────────────────────────────────────────


@router.callback_query(lambda c: c.data == "fsm_cancel")
async def fsm_cancel_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.message.edit_text("❌ Отменено.")
    await cq.answer()


@router.message(Command("cancel"))
async def fsm_cancel_cmd(msg: Message, state: FSMContext):
    current = await state.get_state()
    await state.clear()
    if current:
        await msg.answer("❌ Отменено.")
    else:
        await msg.answer("Нет активного действия.")
