"""Tool implementations for the TransmiBot agent when used from Telegram.

These tools wrap the base tools from `tools.py` and add database logging
for user interactions (plates, address searches) based on phone_number.

This module follows the Single Responsibility Principle:
- Base tools in `tools.py`: pure functionality, no side effects, testable.
- Telegram tools here: add logging/observability layer for production use.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from app.agents.transmi_agent.tools import (
    capture_simit_screenshot as _base_capture_simit_screenshot,
)
from app.agents.transmi_agent.tools import (
    tomtom_find_nearby_services as _base_tomtom_find_nearby_services,
)
from app.agents.transmi_agent.tools import (
    tomtom_find_nearby_services_by_address as _base_tomtom_find_nearby_services_by_address,
)
from app.agents.transmi_agent.tools import (
    tomtom_geocode_address as _base_tomtom_geocode_address,
)
from app.agents.transmi_agent.tools import (
    tomtom_route_with_traffic as _base_tomtom_route_with_traffic,
)
from app.db.crud import (
    log_address_search_by_phone,
    log_plate_by_phone,
)

logger = logging.getLogger(__name__)

# Thread-local storage to pass phone_number from handler to tools
# This avoids polluting tool signatures while allowing logging
_context = threading.local()


def set_user_context(phone_number: str | None) -> None:
    """Set the current user's phone number in thread-local context.

    This should be called from the Telegram handler before invoking the agent.
    """
    _context.phone_number = phone_number


def get_user_context() -> str | None:
    """Get the current user's phone number from thread-local context."""
    return getattr(_context, "phone_number", None)


async def capture_simit_screenshot(plate: str) -> dict[str, Any]:
    """Tool wrapper that delegates to Simit service and logs plate usage.

    This is the Telegram version that includes database logging.
    For ADK testing, use the base version from `tools.py`.
    """

    result = await _base_capture_simit_screenshot(plate=plate)

    # Log plate usage if we have phone_number in context.
    phone_number = get_user_context()
    if phone_number and result.get("status") == "success":
        try:
            # Run sync DB operation in thread to avoid blocking event loop
            await asyncio.to_thread(log_plate_by_phone, phone_number, plate)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log plate lookup by phone")

    return result


async def tomtom_route_with_traffic(
    origin: str,
    destination: str,
) -> dict[str, Any]:
    """Tool wrapper that exposes TomTom routing + live traffic with logging.

    This is the Telegram version that includes database logging.
    For ADK testing, use the base version from `tools.py`.
    """

    result = await _base_tomtom_route_with_traffic(origin=origin, destination=destination)

    # Log both origin and destination addresses when available.
    phone_number = get_user_context()
    if phone_number and result.get("status") == "success":
        try:
            # Run sync DB operations in thread to avoid blocking event loop
            await asyncio.to_thread(
                log_address_search_by_phone, phone_number, origin, "route_origin"
            )
            await asyncio.to_thread(
                log_address_search_by_phone, phone_number, destination, "route_destination"
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log route addresses by phone")

    return result


async def tomtom_find_nearby_services(
    lat: float,
    lon: float,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Tool wrapper que expone la búsqueda de lugares cercanos con logging.

    This is the Telegram version that includes database logging.
    For ADK testing, use the base version from `tools.py`.
    """

    result = await _base_tomtom_find_nearby_services(
        lat=lat,
        lon=lon,
        query=query,
        radius_meters=radius_meters,
    )

    phone_number = get_user_context()
    if phone_number and result.get("status") == "success":
        try:
            # Run sync DB operation in thread to avoid blocking event loop
            await asyncio.to_thread(
                log_address_search_by_phone, phone_number, f"nearby:{query}", "nearby_services"
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log nearby services query by phone")

    return result


async def tomtom_geocode_address(address: str) -> dict[str, Any]:
    """Tool wrapper que devuelve coordenadas con logging.

    This is the Telegram version that includes database logging.
    For ADK testing, use the base version from `tools.py`.
    """

    result = await _base_tomtom_geocode_address(address=address)

    phone_number = get_user_context()
    if phone_number and result.get("status") == "success":
        try:
            # Run sync DB operation in thread to avoid blocking event loop
            await asyncio.to_thread(log_address_search_by_phone, phone_number, address, "geocode")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log geocode query by phone")

    return result


async def tomtom_find_nearby_services_by_address(
    address: str,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Tool wrapper para buscar lugares cercanos por dirección con logging.

    This is the Telegram version that includes database logging.
    For ADK testing, use the base version from `tools.py`.
    """

    result = await _base_tomtom_find_nearby_services_by_address(
        address=address,
        query=query,
        radius_meters=radius_meters,
    )

    phone_number = get_user_context()
    if phone_number and result.get("status") == "success":
        try:
            # Run sync DB operation in thread to avoid blocking event loop
            await asyncio.to_thread(
                log_address_search_by_phone, phone_number, address, "nearby_by_address"
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log nearby-by-address query by phone")

    return result

