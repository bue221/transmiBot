
"""Tool implementations for the TransmiBot agent."""

from __future__ import annotations

import logging
from typing import Any

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


async def capture_simit_screenshot(plate: str) -> dict[str, Any]:
    """Tool wrapper that delegates to the Simit service layer.

    Keeping this thin wrapper makes it easy to reuse the same core logic from
    other parts of the application while presenting a simple tool interface.
    """

    # The service already applies the required error-handling strategy.
    return await capture_simit_screenshot_service(plate=plate)


async def tomtom_route_with_traffic(
    origin: str,
    destination: str,
) -> dict[str, Any]:
    """Tool wrapper that exposes TomTom routing + live traffic to the agent.

    The heavy lifting (validation, error handling, logging, HTTP calls) is delegated
    to the TomTom service layer to keep this tool thin and reusable.
    """

    return await get_route_traffic_summary(origin_text=origin, destination_text=destination)


async def tomtom_find_nearby_services(
    lat: float,
    lon: float,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Tool wrapper que expone la búsqueda de lugares cercanos usando TomTom.

    Pensado para que el agente pueda responder cosas como:
    - "Busca una gasolinera cerca de mi ubicación"
    - "Encuentra parqueaderos a 1km de aquí"
    """

    return await find_nearby_services(
        lat=lat,
        lon=lon,
        query=query,
        radius_meters=radius_meters,
    )


async def tomtom_geocode_address(address: str) -> dict[str, Any]:
    """Tool wrapper que devuelve coordenadas (lat, lon) para una dirección en texto."""

    return await geocode_address(address_text=address)


async def tomtom_find_nearby_services_by_address(
    address: str,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Tool wrapper para buscar lugares cercanos partiendo de una dirección en texto.

    Ejemplos de uso esperados por el agente:
    - "Busca una gasolinera cerca de 'Calle 26 con Avenida 68, Bogotá'"
    - "Encuentra parqueaderos alrededor de 'Portal Eldorado TransMilenio'"
    """

    return await find_nearby_services_by_address(
        address_text=address,
        query=query,
        radius_meters=radius_meters,
    )
