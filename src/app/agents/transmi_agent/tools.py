
"""Tool implementations for the TransmiBot agent."""

from __future__ import annotations

import logging
from typing import Any

from app.db.crud import (
    log_address_search_by_phone,
    log_plate_by_phone,
)
from app.services.simit import capture_simit_screenshot_service
from app.services.tomtom import (
    find_nearby_services,
    find_nearby_services_by_address,
    geocode_address,
    get_route_traffic_summary,
)

logger = logging.getLogger(__name__)


async def get_current_time(city: str) -> dict[str, str]:
    """Mock tool that returns the current time in a specified city."""

    return {"status": "success", "city": city, "time": "10:30 AM", "climate": "sunny"}


async def capture_simit_screenshot(plate: str, phone_number: str | None = None) -> dict[str, Any]:
    """Tool wrapper that delegates to the Simit service layer.

    Keeping this thin wrapper makes it easy to reuse the same core logic from
    other parts of the application while presenting a simple tool interface.
    """

    result = await capture_simit_screenshot_service(plate=plate)

    # Persist plate usage if we know the user's phone number.
    if phone_number:
        try:
            await log_plate_by_phone(phone_number=phone_number, plate=plate)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log plate lookup by phone")

    # The service already applies the required error-handling strategy.
    return result


async def tomtom_route_with_traffic(
    origin: str,
    destination: str,
    phone_number: str | None = None,
) -> dict[str, Any]:
    """Tool wrapper that exposes TomTom routing + live traffic to the agent.

    The heavy lifting (validation, error handling, logging, HTTP calls) is delegated
    to the TomTom service layer to keep this tool thin and reusable.
    """

    result = await get_route_traffic_summary(origin_text=origin, destination_text=destination)

    # Log both origin and destination addresses when available.
    if phone_number and result.get("status") == "success":
        try:
            await log_address_search_by_phone(
                phone_number=phone_number,
                raw_query=origin,
                context="route_origin",
            )
            await log_address_search_by_phone(
                phone_number=phone_number,
                raw_query=destination,
                context="route_destination",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log route addresses by phone")

    return result


async def tomtom_find_nearby_services(
    lat: float,
    lon: float,
    query: str = "gas station",
    radius_meters: int = 2000,
    phone_number: str | None = None,
) -> dict[str, Any]:
    """Tool wrapper que expone la búsqueda de lugares cercanos usando TomTom.

    Pensado para que el agente pueda responder cosas como:
    - "Busca una gasolinera cerca de mi ubicación"
    - "Encuentra parqueaderos a 1km de aquí"
    """

    result = await find_nearby_services(
        lat=lat,
        lon=lon,
        query=query,
        radius_meters=radius_meters,
    )

    if phone_number and result.get("status") == "success":
        try:
            await log_address_search_by_phone(
                phone_number=phone_number,
                raw_query=f"nearby:{query}",
                context="nearby_services",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log nearby services query by phone")

    return result


async def tomtom_geocode_address(address: str, phone_number: str | None = None) -> dict[str, Any]:
    """Tool wrapper que devuelve coordenadas (lat, lon) para una dirección en texto."""

    result = await geocode_address(address_text=address)

    if phone_number and result.get("status") == "success":
        try:
            await log_address_search_by_phone(
                phone_number=phone_number,
                raw_query=address,
                context="geocode",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log geocode query by phone")

    return result


async def tomtom_find_nearby_services_by_address(
    address: str,
    query: str = "gas station",
    radius_meters: int = 2000,
    phone_number: str | None = None,
) -> dict[str, Any]:
    """Tool wrapper para buscar lugares cercanos partiendo de una dirección en texto.

    Ejemplos de uso esperados por el agente:
    - "Busca una gasolinera cerca de 'Calle 26 con Avenida 68, Bogotá'"
    - "Encuentra parqueaderos alrededor de 'Portal Eldorado TransMilenio'"
    """

    result = await find_nearby_services_by_address(
        address_text=address,
        query=query,
        radius_meters=radius_meters,
    )

    if phone_number and result.get("status") == "success":
        try:
            await log_address_search_by_phone(
                phone_number=phone_number,
                raw_query=address,
                context="nearby_by_address",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to log nearby-by-address query by phone")

    return result
