"""
Configuration — loaded once from environment variables.
Copy .env.example → .env and fill in your values.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])
    allowed_user_id: int = field(
        default_factory=lambda: int(os.getenv("ALLOWED_USER_ID", "0"))
    )
    data_file: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_FILE", "data/pushups.json"))
    )
    timezone: ZoneInfo = field(
        default_factory=lambda: ZoneInfo(os.getenv("TZ", "Europe/Moscow"))
    )
    daily_goal: int = field(default_factory=lambda: int(os.getenv("DAILY_GOAL", "100")))

    def __post_init__(self) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    def allowed(self, user_id: int) -> bool:
        return self.allowed_user_id == 0 or user_id == self.allowed_user_id


# Singleton
settings = Settings()
