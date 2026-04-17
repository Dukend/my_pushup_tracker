"""
keyboards.py — all InlineKeyboardMarkup builders in one place.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """Main menu keyboard — shown with /menu or /start."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="today"),
                InlineKeyboardButton(text="🏋 Всего", callback_data="total"),
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
                InlineKeyboardButton(text="📆 7 дней", callback_data="history"),
            ],
            [
                InlineKeyboardButton(text="🎯 Цель", callback_data="goal"),
                InlineKeyboardButton(text="🏆 Рекорд", callback_data="record"),
            ],
            [
                InlineKeyboardButton(text="⏰ Напоминания", callback_data="reminders_list"),
                InlineKeyboardButton(text="📋 Задачи", callback_data="todo_list"),
            ],
            [
                InlineKeyboardButton(text="➕ +20", callback_data="quick_20"),
                InlineKeyboardButton(text="➕ +30", callback_data="quick_30"),
                InlineKeyboardButton(text="➕ +40", callback_data="quick_40"),
                InlineKeyboardButton(text="➕ +50", callback_data="quick_50"),
            ],
            [
                InlineKeyboardButton(text="↩️ Отмена", callback_data="undo"),
            ],
        ]
    )


def reminders_menu(reminders: dict) -> InlineKeyboardMarkup:
    """Dynamic keyboard listing all reminders with toggle + delete."""
    rows = []
    for key, r in reminders.items():
        icon = "✅" if r["enabled"] else "🔕"
        label = r["label"]
        time = r["time"]
        toggle_cb = f"rem_toggle_{key}"
        row = [InlineKeyboardButton(text=f"{icon} {label} {time}", callback_data=f"rem_info_{key}")]
        if r.get("custom"):
            row.append(InlineKeyboardButton(text="🗑", callback_data=f"rem_delete_{key}"))
        else:
            toggle_text = "Выкл" if r["enabled"] else "Вкл"
            row.append(InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb))
        rows.append(row)

    rows.append([InlineKeyboardButton(text="➕ Новое напоминание", callback_data="rem_new_fsm")])
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="« Меню", callback_data="main_menu"),
            ]
        ]
    )


def back_to_reminders() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="« Напоминания", callback_data="reminders_list"),
                InlineKeyboardButton(text="« Меню", callback_data="main_menu"),
            ]
        ]
    )


def confirm_delete(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"rem_confirm_delete_{key}"),
                InlineKeyboardButton(text="Отмена", callback_data="reminders_list"),
            ]
        ]
    )
