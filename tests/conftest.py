from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_events() -> dict:
    with (PROJECT_ROOT / "data" / "cloudtrail_events.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


@pytest.fixture
def event_labels() -> dict:
    with (PROJECT_ROOT / "data" / "root_login_without_mfa_labels.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


@pytest.fixture
def additional_events() -> dict:
    with (PROJECT_ROOT / "data" / "additional_security_events.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


@pytest.fixture
def additional_event_labels() -> dict:
    with (PROJECT_ROOT / "data" / "additional_security_event_labels.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_path = (tmp_path / "cloudsec-test.db").as_posix()
    app = create_app(
        settings=Settings(app_env="test", database_url=f"sqlite:///{database_path}")
    )
    with TestClient(app) as test_client:
        yield test_client
