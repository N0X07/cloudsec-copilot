from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def database_url_from_env() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    host = os.getenv("DB_HOST")
    if not host:
        return "sqlite:///./cloudsec.db"

    password = os.getenv("DB_PASSWORD")
    if password is None:
        raise ValueError("DB_PASSWORD is required when DB_HOST is configured")
    user = quote_plus(os.getenv("DB_USER", "cloudsecadmin"))
    encoded_password = quote_plus(password)
    port = os.getenv("DB_PORT", "5432")
    database = quote_plus(os.getenv("DB_NAME", "cloudsec"))
    return (
        f"postgresql+psycopg://{user}:{encoded_password}@{host}:{port}/{database}"
    )


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
            database_url=database_url_from_env(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra"),
            max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "4")),
        )
