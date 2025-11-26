from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """Application user identified by Telegram ID."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    # Optional user data
    phone_number = Column(String(50), nullable=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    plates = relationship("Plate", back_populates="user", cascade="all, delete-orphan")
    address_searches = relationship(
        "AddressSearch",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Interaction(Base):
    """Represents a message interaction (user or assistant)."""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Denormalized for easier querying by telegram_id without joins.
    telegram_id = Column(BigInteger, index=True, nullable=False)

    message_text = Column(Text, nullable=False)
    # 'user' for messages from the user, 'assistant' for bot responses
    role = Column(String(20), nullable=False, default="user", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="interactions")


class Plate(Base):
    """License plates associated with a user."""

    __tablename__ = "plates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    telegram_id = Column(BigInteger, index=True, nullable=False)

    plate = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="plates")


class AddressSearch(Base):
    """Free-text address searches a user has performed."""

    __tablename__ = "address_searches"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    telegram_id = Column(BigInteger, index=True, nullable=False)

    raw_query = Column(Text, nullable=False)
    context = Column(String(50), nullable=True)  # e.g. "geocode", "route", "nearby_by_address"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="address_searches")


