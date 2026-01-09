"""Runner configuration."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Runner settings from environment variables."""

    bot_id: str = ""
    telegram_token: str = ""
    api_url: str = ""
    runner_secret: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    def __init__(self):
        self.bot_id = os.getenv("BOT_ID", "")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        self.api_url = os.getenv("API_URL", "http://api:8000")
        self.runner_secret = os.getenv("RUNNER_SECRET", "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
