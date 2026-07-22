from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite:///./cloudsec.db"
    openai_model: str = "gpt-5.6-terra"
    max_agent_steps: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./cloudsec.db"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra"),
            max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "4")),
        )
