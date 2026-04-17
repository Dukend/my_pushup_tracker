"""
Pushup Tracker Bot — entry point.
Run: python main.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import settings
from bot.handlers import commands, fsm, inline, reminders_cmd, todo
from bot.scheduler import reminder_loop
from bot.storage import Storage
from bot.todo import TodoStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def _set_commands(bot: Bot) -> None:
    """#11 — register command hints visible in Telegram UI."""
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="add", description="Добавить отжимания: /add 30"),
        BotCommand(command="stats", description="Полная статистика"),
        BotCommand(command="today", description="Счётчик за сегодня"),
        BotCommand(command="history", description="Последние 7 дней"),
        BotCommand(command="goal", description="Посмотреть / изменить цель"),
        BotCommand(command="record", description="Личный рекорд за день"),
        BotCommand(command="undo", description="Отменить последнее добавление"),
        BotCommand(command="todo", description="Список задач"),
        BotCommand(command="new", description="Добавить задачу (диалог)"),
        BotCommand(command="remind", description="Управление напоминаниями"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
    ])
    log.info("Bot commands registered")


async def main() -> None:
    log.info("Starting Pushup Tracker Bot…")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    storage = Storage(settings.data_file)
    todo_st = TodoStorage(settings.data_file)

    # Single instances shared across all handlers via DI
    dp["storage"] = storage
    dp["todo"] = todo_st

    # Register routers
    dp.include_router(fsm.router)  # FSM must be before commands to catch states
    dp.include_router(commands.router)
    dp.include_router(inline.router)
    dp.include_router(reminders_cmd.router)
    dp.include_router(todo.router)

    # Register bot commands in Telegram (shows hints when typing /)
    await _set_commands(bot)

    # Start background scheduler
    asyncio.create_task(reminder_loop(bot, storage, todo_st, settings))

    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
