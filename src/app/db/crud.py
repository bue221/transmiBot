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
def get_or_create_user_by_phone(
    session,
    phone_number: str,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User | None:
    """Return existing user by phone or create a new one."""

    phone = (phone_number or "").strip()
    if not phone:
        return None

    user = session.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()

    if user is None:
        user = User(
            phone_number=phone,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
    else:
        # Update basic data if new values arrive
        if telegram_id is not None:
            user.telegram_id = telegram_id
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

    return user


@_with_session
def log_interaction_by_phone(session, phone_number: str, message_text: str) -> None:
    """Persist a single interaction message for the given phone number."""

    phone = (phone_number or "").strip()
    if not phone:
        return

    user = session.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()
    if user is None:
        user = User(phone_number=phone)
        session.add(user)

    session.add(
        Interaction(
            user=user,
            phone_number=phone,
            message_text=message_text or "",
        )
    )


@_with_session
def log_plate_by_phone(session, phone_number: str, plate: str) -> None:
    """Persist a plate lookup for the given phone number."""

    phone = (phone_number or "").strip()
    if not phone:
        return

    user = session.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()
    if user is None:
        user = User(phone_number=phone)
        session.add(user)

    session.add(
        Plate(
            user=user,
            phone_number=phone,
            plate=(plate or "").strip().upper(),
        )
    )


@_with_session
def log_address_search_by_phone(
    session,
    phone_number: str,
    raw_query: str,
    context: str,
) -> None:
    """Persist an address search (geocode / route / nearby) for the given phone number."""

    phone = (phone_number or "").strip()
    if not phone:
        return

    user = session.execute(select(User).where(User.phone_number == phone)).scalar_one_or_none()
    if user is None:
        user = User(phone_number=phone)
        session.add(user)

    session.add(
        AddressSearch(
            user=user,
            phone_number=phone,
            raw_query=raw_query or "",
            context=context or "",
        )
    )


