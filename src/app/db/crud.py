from __future__ import annotations

from typing import Callable

from sqlalchemy import select

from app.db.models import AddressSearch, Interaction, Plate, User
from app.db.session import SessionLocal


def _with_session(fn: Callable):
    """Simple decorator to manage DB session lifecycle and error handling."""

    def wrapper(*args, **kwargs):
        from logging import getLogger

        logger = getLogger(__name__)
        session = SessionLocal()
        try:
            result = fn(session, *args, **kwargs)
            session.commit()
            return result
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.exception("Database operation failed")
            return None
        finally:
            session.close()

    return wrapper


@_with_session
def get_or_create_user_by_telegram_id(
    session,
    telegram_id: int,
    *,
    phone_number: str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User | None:
    """Return existing user by telegram_id or create a new one."""

    if telegram_id is None:
        return None

    user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()

    if user is None:
        # Create new user with telegram_id as primary identifier
        phone = (phone_number or "").strip() if phone_number else None
        user = User(
            telegram_id=telegram_id,
            phone_number=phone,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
    else:
        # Update basic data if new values arrive
        if phone_number:
            phone = (phone_number or "").strip()
            if phone:
                user.phone_number = phone
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

    return user


@_with_session
def log_interaction_by_telegram_id(
    session,
    telegram_id: int,
    message_text: str,
    role: str = "user",
) -> None:
    """Persist a single interaction message (user or assistant) for the given telegram_id.

    Args:
        session: Database session (injected by decorator).
        telegram_id: Telegram user ID.
        message_text: Message content.
        role: 'user' for user messages, 'assistant' for bot responses.
    """

    if telegram_id is None:
        return

    user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
    if user is None:
        # Create user if doesn't exist
        user = User(telegram_id=telegram_id)
        session.add(user)

    session.add(
        Interaction(
            user=user,
            telegram_id=telegram_id,
            message_text=message_text or "",
            role=role,
        )
    )


@_with_session
def log_plate_by_telegram_id(session, telegram_id: int, plate: str) -> None:
    """Persist a plate lookup for the given telegram_id."""

    if telegram_id is None:
        return

    user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)

    session.add(
        Plate(
            user=user,
            telegram_id=telegram_id,
            plate=(plate or "").strip().upper(),
        )
    )


@_with_session
def log_address_search_by_telegram_id(
    session,
    telegram_id: int,
    raw_query: str,
    context: str,
) -> None:
    """Persist an address search (geocode / route / nearby) for the given telegram_id."""

    if telegram_id is None:
        return

    user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)

    session.add(
        AddressSearch(
            user=user,
            telegram_id=telegram_id,
            raw_query=raw_query or "",
            context=context or "",
        )
    )


