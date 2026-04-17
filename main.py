"""
Pushup Tracker Bot — entry point.
Run: python main.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import commands, inline, reminders_cmd, todo
from bot.scheduler import reminder_loop
from bot.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def main() -> None:
    log.info("Starting Pushup Tracker Bot…")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    storage = Storage(settings.data_file)

    # Register routers
    dp.include_router(commands.router)
    dp.include_router(inline.router)
    dp.include_router(reminders_cmd.router)
    dp.include_router(todo.router)

    # Start background scheduler
    asyncio.create_task(reminder_loop(bot, storage, settings))

    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
