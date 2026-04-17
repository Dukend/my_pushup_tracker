"""
handlers/todo.py — /todo commands and inline callbacks for the todo list.

Commands
--------
/todo                   — show active tasks (same as button)
/todo add Купить хлеб   — add normal-priority task
/todo add ! Купить хлеб — add high-priority task  (leading !)
/todo done <id>         — mark done
/todo del  <id>         — delete
/todo edit <id> New text — edit text
/todo all               — show active + completed today

Inline callbacks (all prefixed todo_)
--------------------------------------
todo_list               — refresh active list
todo_done_<id>          — mark done
todo_undone_<id>        — mark not done
todo_del_<id>           — delete (with confirm)
todo_confirm_del_<id>   — confirmed delete
todo_hi_<id>            — set high priority
todo_norm_<id>          — set normal priority
todo_new                — prompt to add new task
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.todo import TodoStorage

router = Router()
storage = TodoStorage(settings.data_file)

# ── Keyboard builders ─────────────────────────────────────────────────────────


def _task_row(t: dict) -> list[InlineKeyboardButton]:
    """One row per task: [✅/↩ text] [⬆/⬇ priority] [🗑]"""
    tid = t["id"]
    pri_icon = "🔴" if t["priority"] == "high" else "⚪"
    label = f"{'✅ ' if t['done'] else ''}{pri_icon} {t['text'][:35]}"

    toggle_cb = f"todo_undone_{tid}" if t["done"] else f"todo_done_{tid}"
    toggle_tx = "↩" if t["done"] else "✓"

    pri_cb = f"todo_norm_{tid}" if t["priority"] == "high" else f"todo_hi_{tid}"
    pri_tx = "⬇ приор." if t["priority"] == "high" else "⬆ приор."

    return [
        InlineKeyboardButton(text=label, callback_data=f"todo_info_{tid}"),
        InlineKeyboardButton(text=toggle_tx, callback_data=toggle_cb),
        InlineKeyboardButton(text=pri_tx, callback_data=pri_cb),
        InlineKeyboardButton(text="🗑", callback_data=f"todo_del_{tid}"),
    ]


def todo_list_kb(tasks: list[dict], show_done: bool = False) -> InlineKeyboardMarkup:
    rows = [_task_row(t) for t in tasks]
    rows.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="todo_new"),
        InlineKeyboardButton(text="📋 + выполненные", callback_data="todo_all"),
    ])
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def todo_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить задачу", callback_data="todo_new")],
            [InlineKeyboardButton(text="« Меню", callback_data="main_menu")],
        ]
    )


def confirm_del_kb(tid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"todo_confirm_del_{tid}"),
                InlineKeyboardButton(text="Отмена", callback_data="todo_list"),
            ]
        ]
    )


def back_todo_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="« Список задач", callback_data="todo_list"),
                InlineKeyboardButton(text="« Меню", callback_data="main_menu"),
            ]
        ]
    )


# ── Formatters ────────────────────────────────────────────────────────────────


def _fmt_list(tasks: list[dict], title: str = "📋 <b>Задачи</b>") -> str:
    if not tasks:
        return f"{title}\n\n<i>Список пуст.</i>"
    lines = [title, ""]
    for t in tasks:
        pri = "🔴" if t["priority"] == "high" else "⚪"
        done = "✅ <s>" if t["done"] else ""
        end = "</s>" if t["done"] else ""
        lines.append(f"{pri} {done}{t['text']}{end}  <code>{t['id']}</code>")
    return "\n".join(lines)


def _fmt_active(tasks: list[dict]) -> str:
    s = storage.stats(settings.timezone)
    header = (
        f"📋 <b>Задачи</b>  "
        f"[активных: {s['active']}  🔴 важных: {s['high']}  ✅ сегодня: {s['done_today']}]"
    )
    return _fmt_list(tasks, header)


# ── Guard ─────────────────────────────────────────────────────────────────────


def guard_msg(msg: Message) -> bool:
    return settings.allowed(msg.from_user.id)


def guard_cb(cq: CallbackQuery) -> bool:
    return settings.allowed(cq.from_user.id)


# ── /todo command ─────────────────────────────────────────────────────────────


@router.message(Command("todo"))
async def cmd_todo(msg: Message):
    if not guard_msg(msg):
        return

    raw = (msg.text or "").strip()
    parts = raw.split(maxsplit=2)
    sub = parts[1].lower() if len(parts) > 1 else None

    # /todo  →  show list
    if sub is None:
        tasks = storage.get_active()
        await msg.answer(
            _fmt_active(tasks),
            parse_mode="HTML",
            reply_markup=todo_list_kb(tasks) if tasks else todo_empty_kb(),
        )
        return

    # /todo add [!] text
    if sub == "add":
        if len(parts) < 3:
            await msg.answer(
                "Использование:\n"
                "/todo add Купить хлеб\n"
                "/todo add ! Срочная задача  (высокий приоритет)",
                reply_markup=back_todo_kb(),
            )
            return
        rest = parts[2].strip()
        priority = "normal"
        if rest.startswith("!"):
            priority = "high"
            rest = rest[1:].strip()
        if not rest:
            await msg.answer("Текст задачи не может быть пустым.")
            return
        if len(rest) > 200:
            await msg.answer("Слишком длинный текст (макс. 200 символов).")
            return
        item = storage.add(rest, priority)
        pri = "🔴 Важная" if item["priority"] == "high" else "⚪ Обычная"
        await msg.answer(
            f"➕ Добавлено: <b>{item['text']}</b>\n{pri}",
            parse_mode="HTML",
            reply_markup=back_todo_kb(),
        )
        return

    # /todo done <id>
    if sub == "done":
        tid = parts[2].strip() if len(parts) > 2 else ""
        if not tid or not storage.complete(tid):
            await msg.answer("Задача не найдена или уже выполнена.")
            return
        await msg.answer("✅ Выполнено!", reply_markup=back_todo_kb())
        return

    # /todo del <id>
    if sub == "del":
        tid = parts[2].strip() if len(parts) > 2 else ""
        if not tid or not storage.delete(tid):
            await msg.answer("Задача не найдена.")
            return
        await msg.answer("🗑 Удалено.", reply_markup=back_todo_kb())
        return

    # /todo edit <id> new text
    if sub == "edit":
        rest = parts[2].strip() if len(parts) > 2 else ""
        ep = rest.split(maxsplit=1)
        if len(ep) < 2:
            await msg.answer("Использование: /todo edit <id> Новый текст")
            return
        tid, new_text = ep[0], ep[1].strip()
        if not storage.edit(tid, new_text):
            await msg.answer("Задача не найдена.")
            return
        await msg.answer(
            f"✏️ Обновлено: <b>{new_text}</b>",
            parse_mode="HTML",
            reply_markup=back_todo_kb(),
        )
        return

    # /todo all  — active + done today
    if sub == "all":
        tasks = storage.get_all()
        await msg.answer(
            _fmt_list(tasks, "📋 <b>Все задачи (сегодня)</b>"),
            parse_mode="HTML",
            reply_markup=todo_list_kb([t for t in tasks if not t["done"]]),
        )
        return

    await msg.answer("Подкоманды: add, done, del, edit, all\nПример: /todo add Купить молоко")


# ── Inline callbacks ──────────────────────────────────────────────────────────


async def _refresh(cq: CallbackQuery):
    """Re-render the active task list in-place."""
    tasks = storage.get_active()
    text = _fmt_active(tasks)
    kb = todo_list_kb(tasks) if tasks else todo_empty_kb()
    try:
        await cq.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cq.answer()


@router.callback_query(lambda c: c.data == "todo_list")
async def cb_todo_list(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    await _refresh(cq)


@router.callback_query(lambda c: c.data == "todo_all")
async def cb_todo_all(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tasks = storage.get_all()
    text = _fmt_list(tasks, "📋 <b>Все задачи (сегодня)</b>")
    kb = todo_list_kb([t for t in tasks if not t["done"]])
    try:
        await cq.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cq.answer()


@router.callback_query(lambda c: c.data == "todo_new")
async def cb_todo_new(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    await cq.message.answer(
        "➕ <b>Новая задача</b>\n\n"
        "Отправь:\n"
        "<code>/todo add Текст задачи</code>\n\n"
        "Для высокого приоритета:\n"
        "<code>/todo add ! Срочная задача</code>",
        parse_mode="HTML",
        reply_markup=back_todo_kb(),
    )
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("todo_done_"))
async def cb_todo_done(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_done_")
    storage.complete(tid)
    await cq.answer("✅ Выполнено!")
    await _refresh(cq)


@router.callback_query(lambda c: c.data.startswith("todo_undone_"))
async def cb_todo_undone(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_undone_")
    storage.uncomplete(tid)
    await cq.answer("↩ Отмечено как активное")
    await _refresh(cq)


@router.callback_query(lambda c: c.data.startswith("todo_hi_"))
async def cb_todo_hi(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_hi_")
    storage.set_priority(tid, "high")
    await cq.answer("🔴 Высокий приоритет")
    await _refresh(cq)


@router.callback_query(lambda c: c.data.startswith("todo_norm_"))
async def cb_todo_norm(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_norm_")
    storage.set_priority(tid, "normal")
    await cq.answer("⚪ Обычный приоритет")
    await _refresh(cq)


@router.callback_query(lambda c: c.data.startswith("todo_del_"))
async def cb_todo_del(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_del_")
    data = storage._load()  # noqa: SLF001
    item = data.get("todos", {}).get(tid)
    text = item["text"] if item else tid
    try:
        await cq.message.edit_text(
            f"🗑 Удалить задачу?\n\n<b>{text}</b>",
            parse_mode="HTML",
            reply_markup=confirm_del_kb(tid),
        )
    except Exception:
        await cq.message.answer(
            f"🗑 Удалить задачу?\n\n<b>{text}</b>",
            parse_mode="HTML",
            reply_markup=confirm_del_kb(tid),
        )
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("todo_confirm_del_"))
async def cb_todo_confirm_del(cq: CallbackQuery):
    if not guard_cb(cq):
        return
    tid = cq.data.removeprefix("todo_confirm_del_")
    storage.delete(tid)
    await cq.answer("🗑 Удалено")
    await _refresh(cq)


@router.callback_query(lambda c: c.data.startswith("todo_info_"))
async def cb_todo_info(cq: CallbackQuery):
    """Tap on task label — do nothing visible, just ack."""
    await cq.answer()
