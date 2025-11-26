"""TomTom routing and geocoding service functions.

This module encapsulates all interaction with the TomTom APIs so that higher layers
(tools, agents, handlers) can depend on a single, well-defined service boundary.

Error-handling strategy:
- Input validation errors return a structured response with ``status="error"`` and
  ``error_type="validation"``.
- Network / HTTP issues return ``error_type="network"`` or ``error_type="http"``.
- Unexpected issues are captured under ``error_type="unexpected"``.

All successful responses use ``status="success"`` and avoid raising exceptions so
that callers (e.g. the agent tools) can safely surface human‑friendly messages.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_SEARCH_BASE_URL = "https://api.tomtom.com/search/2/search"
_ROUTING_BASE_URL = "https://api.tomtom.com/routing/1/calculateRoute"
_DEFAULT_TIMEOUT_SECONDS = 10.0


def _error_response(error_type: str, message: str, details: str | None = None) -> dict[str, Any]:
    """Build a standardized error response."""
    result = {"status": "error", "error_type": error_type, "message": message}
    if details:
        result["details"] = details
    return result


def _validate_string(value: str, field_name: str) -> dict[str, Any] | None:
    """Validate that a string is not empty."""
    if not value or not value.strip():
        return _error_response("validation", f"Debes indicar {field_name}.")
    return None


def _get_api_key() -> tuple[str | None, dict[str, Any] | None]:
    """Get TomTom API key from settings, or return error if not configured."""
    settings = get_settings()
    api_key = getattr(settings, "tomtom_api_key", None)
    if not api_key:
        logger.error("TomTom API key is not configured")
        return None, _error_response(
            "configuration", "La API key de TomTom no está configurada en el servidor."
        )
    return api_key, None


async def _make_request(
    url: str,
    params: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Make an HTTP GET request and handle errors consistently."""
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return {"status": "success", "response": response}
    except httpx.RequestError as exc:
        logger.exception("Network error", extra=context)
        return _error_response("network", "No fue posible comunicarse con el servicio.", str(exc))
    except httpx.HTTPStatusError as exc:
        logger.exception("HTTP error", extra={**context, "status_code": exc.response.status_code})
        return _error_response("http", "El servicio respondió con un error.", str(exc))


async def _geocode_address(address: str) -> dict[str, Any]:
    """Resolve a free‑text address into latitude/longitude using TomTom Search API.

    Returns a dict with:
    - status: "success" | "error"
    - On success: lat, lon, coordinates
    - On error: error_type, message, details (optional)
    """
    if validation_error := _validate_string(address, "la dirección"):
        return validation_error

    api_key, key_error = _get_api_key()
    if key_error:
        return key_error

    query = address.strip()
    encoded_query = quote(query, safe="")
    url = f"{_SEARCH_BASE_URL}/{encoded_query}.json"
    params = {"key": api_key, "limit": 1}

    request_result = await _make_request(url, params, {"address": query})
    if request_result.get("status") != "success":
        return request_result

    response = request_result["response"]
    try:
        data = response.json()
    except ValueError as exc:
        logger.exception("Failed to decode response", extra={"address": query})
        return _error_response("parse", "No se pudo interpretar la respuesta.", str(exc))

    results = data.get("results") or []
    if not results:
        logger.info("No geocoding results found", extra={"address": query})
        return _error_response("not_found", "No encontré una ubicación para esa dirección.")

    position = results[0].get("position") or {}
    lat = position.get("lat")
    lon = position.get("lon")

    if lat is None or lon is None:
        logger.warning("Missing position field", extra={"address": query})
        return _error_response("parse", "La respuesta no contenía coordenadas válidas.")

    coordinates = f"{lat},{lon}"
    logger.info("Resolved address", extra={"address": query, "lat": lat, "lon": lon})

    return {"status": "success", "lat": lat, "lon": lon, "coordinates": coordinates}


def _parse_route_data(data: dict[str, Any]) -> dict[str, Any]:
    """Parse route data from TomTom API response into summary metrics."""
    routes = data.get("routes") or []
    if not routes:
        return _error_response("not_found", "No se encontró una ruta entre los puntos indicados.")

    summary = routes[0].get("summary") or {}
    try:
        total_seconds = int(summary.get("travelTimeInSeconds", 0))
        delay_seconds = int(summary.get("trafficDelayInSeconds", 0))
        distance_meters = int(summary.get("lengthInMeters", 0))
        arrival_time_iso = summary.get("arrivalTime")
    except (TypeError, ValueError) as exc:
        logger.exception("Invalid route summary data", extra={"summary": summary})
        return _error_response("parse", "Los datos de la ruta recibidos no son válidos.", str(exc))

    return {
        "status": "success",
        "minutes_total": round(total_seconds / 60) if total_seconds > 0 else 0,
        "minutes_delay": round(delay_seconds / 60) if delay_seconds > 0 else 0,
        "distance_km": round(distance_meters / 1000, 1) if distance_meters > 0 else 0.0,
        "traffic_detected": delay_seconds > 0,
        "arrival_time_iso": arrival_time_iso,
    }


async def get_route_traffic_summary(
    origin_text: str,
    destination_text: str,
) -> dict[str, Any]:
    """Calculate route and live traffic information between two addresses.

    Returns a dict with status="success" and route metrics, or status="error" with error details.
    """
    if validation_error := _validate_string(origin_text, "la dirección de origen"):
        return validation_error

    if validation_error := _validate_string(destination_text, "la dirección de destino"):
        return validation_error

    origin_geo = await _geocode_address(origin_text)
    if origin_geo.get("status") != "success":
        return _error_response(
            origin_geo.get("error_type", "geocoding"),
            f"No pude localizar la dirección de origen: {origin_text}",
        )

    dest_geo = await _geocode_address(destination_text)
    if dest_geo.get("status") != "success":
        return _error_response(
            dest_geo.get("error_type", "geocoding"),
            f"No pude localizar la dirección de destino: {destination_text}",
        )

    origin_coords = origin_geo["coordinates"]
    dest_coords = dest_geo["coordinates"]

    api_key, key_error = _get_api_key()
    if key_error:
        return key_error

    route_url = f"{_ROUTING_BASE_URL}/{origin_coords}:{dest_coords}/json"
    params = {"key": api_key, "traffic": "true", "travelMode": "car", "routeType": "fastest"}

    request_result = await _make_request(
        route_url, params, {"origin": origin_coords, "destination": dest_coords}
    )
    if request_result.get("status") != "success":
        return request_result

    response = request_result["response"]
    try:
        data = response.json()
    except ValueError as exc:
        logger.exception(
            "Failed to decode response",
            extra={"origin": origin_coords, "destination": dest_coords},
        )
        return _error_response("parse", "No se pudo interpretar la respuesta.", str(exc))

    route_data = _parse_route_data(data)
    if route_data.get("status") != "success":
        return route_data

    logger.info(
        "Computed route summary",
        extra={
            "origin": origin_text,
            "destination": destination_text,
            "minutes_total": route_data["minutes_total"],
            "minutes_delay": route_data["minutes_delay"],
            "distance_km": route_data["distance_km"],
        },
    )

    return {
        **route_data,
        "origin": origin_text,
        "destination": destination_text,
        "origin_coordinates": origin_coords,
        "destination_coordinates": dest_coords,
    }

