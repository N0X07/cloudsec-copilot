from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Database:
    """Owns the SQLAlchemy engine and session factory for one application."""

    def __init__(self, url: str) -> None:
        engine_options: dict[str, object] = {"pool_pre_ping": True}

        if url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if url in {"sqlite://", "sqlite:///:memory:"}:
                engine_options["poolclass"] = StaticPool

        self.engine: Engine = create_engine(url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Generator[Session, None, None]:
        db_session = self.session_factory()
        try:
            yield db_session
        finally:
            db_session.close()

    def dispose(self) -> None:
        self.engine.dispose()

