from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Base directory two levels up: .../transmiBot/
BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "var"
DB_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_DIR / 'transmibot.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def init_db() -> None:
    """Create database tables if they don't exist (idempotent)."""

    # Import models so they are registered with SQLAlchemy's metadata
    from app.db import models  # noqa: F401

    models  # silence linters
    Base.metadata.create_all(bind=engine)


