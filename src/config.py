from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Application configuration loaded from environment variables."""

    database_url: str

    @classmethod
    def load(cls) -> "Settings":
        url = os.getenv("BTRAINER_DATABASE_URL")
        if not url:
            raise RuntimeError(
                "Missing BTRAINER_DATABASE_URL environment variable. "
                "Example: postgresql+psycopg://user:pass@localhost:5432/btrainer"
            )
        return cls(database_url=url)


settings = Settings.load()
