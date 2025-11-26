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
_POI_SEARCH_BASE_URL = "https://api.tomtom.com/search/2/search"
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

    minutes_total = round(total_seconds / 60) if total_seconds > 0 else 0
    minutes_delay = round(delay_seconds / 60) if delay_seconds > 0 else 0
    distance_km = round(distance_meters / 1000, 1) if distance_meters > 0 else 0.0

    parts: list[str] = []
    if distance_km:
        parts.append(f"aprox. {distance_km} km")
    if minutes_total:
        parts.append(f"{minutes_total} min de trayecto")
    if minutes_delay:
        parts.append(f"con {minutes_delay} min de tráfico")
    summary_text = ", ".join(parts) if parts else "No se pudo calcular un resumen de la ruta."

    return {
        "status": "success",
        "minutes_total": minutes_total,
        "minutes_delay": minutes_delay,
        "distance_km": distance_km,
        "traffic_detected": delay_seconds > 0,
        "arrival_time_iso": arrival_time_iso,
        "summary_text": summary_text,
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

    result = {
        **route_data,
        "origin": origin_text,
        "destination": destination_text,
        "origin_coordinates": origin_coords,
        "destination_coordinates": dest_coords,
    }

    # Texto listo para mostrar al usuario. El agente puede reutilizarlo directamente.
    result["user_friendly_summary"] = (
        f"Entre '{origin_text}' y '{destination_text}' la ruta es de "
        f"{route_data['distance_km']} km y toma aproximadamente "
        f"{route_data['minutes_total']} minutos"
        f"{' (incluye tráfico)' if route_data['traffic_detected'] else ''}."
    )

    return result


async def find_nearby_services(
    lat: float,
    lon: float,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Busca servicios cercanos alrededor de una ubicación.

    Args:
        lat: Latitud del centro de búsqueda.
        lon: Longitud del centro de búsqueda.
        query: Término de búsqueda (ej: "gas station", "parking", "mechanic", "atm").
        radius_meters: Radio de búsqueda en metros (default 2km).

    Returns:
        Respuesta estándar con:
        - status: "success" | "error"
        - En success: lista de lugares encontrados bajo la clave "places".
    """

    api_key, key_error = _get_api_key()
    if key_error:
        return key_error

    # URL específica para búsqueda de POIs
    # Encodeamos el query para evitar errores con espacios
    encoded_query = quote(query, safe="")
    url = f"{_POI_SEARCH_BASE_URL}/{encoded_query}.json"

    params = {
        "key": api_key,
        "lat": lat,
        "lon": lon,
        "radius": radius_meters,
        "limit": 5,  # Traemos solo los 5 más cercanos para no saturar al usuario
        "idxSet": "POI",  # Importante: Solo buscar Puntos de Interés, no direcciones
    }

    request_result = await _make_request(
        url,
        params,
        {"context": "poi_search", "query": query, "lat": lat, "lon": lon},
    )

    if request_result.get("status") != "success":
        return request_result

    response = request_result["response"]

    try:
        data = response.json()
    except ValueError as exc:
        logger.exception("Failed to decode POI response")
        return _error_response(
            "parse",
            "No se pudo interpretar la respuesta de lugares cercanos.",
            str(exc),
        )

    results = data.get("results") or []

    if not results:
        return {
            "status": "success",
            "message": f"No encontré '{query}' en un radio de {radius_meters}m.",
            "places": [],
            "summary_text": (
                f"No encontré lugares de tipo '{query}' cerca de las coordenadas "
                f"({lat}, {lon}) en un radio de {radius_meters} metros."
            ),
        }

    # Procesamos los resultados para devolver solo lo útil al agente
    places: list[dict[str, Any]] = []
    for item in results:
        poi = item.get("poi", {}) or {}
        address = item.get("address", {}) or {}
        dist = item.get("dist", 0) or 0  # Distancia en metros desde el punto central

        categories = poi.get("categories") or ["General"]

        place_info = {
            "name": poi.get("name", "Servicio sin nombre"),
            "address": address.get("freeformAddress", "Dirección no disponible"),
            "distance_meters": dist,
            "distance_text": f"{round(dist)} metros",
            # A veces es útil dar la categoría exacta (ej: "Petrol Station" vs "EV Charging")
            "category": categories[0],
        }
        places.append(place_info)

    logger.info(
        "Found nearby services",
        extra={
            "query": query,
            "lat": lat,
            "lon": lon,
            "radius_meters": radius_meters,
            "count": len(places),
        },
    )

    # Construimos un resumen textual amigable para que el agente lo pueda usar tal cual.
    max_listed = min(len(places), 5)
    places_lines = []
    for idx, place in enumerate(places[:max_listed], start=1):
        places_lines.append(
            f"{idx}. {place['name']} – {place['address']} "
            f"({place['distance_text']})"
        )

    summary_header = (
        f"Encontré {len(places)} lugar(es) de tipo '{query}' "
        f"en un radio de {radius_meters} metros."
    )
    summary_text = summary_header
    if places_lines:
        summary_text += "\n" + "\n".join(places_lines)

    return {
        "status": "success",
        "places": places,
        "search_radius": radius_meters,
        "query": query,
        "center": {"lat": lat, "lon": lon},
        "summary_text": summary_text,
    }


async def geocode_address(address_text: str) -> dict[str, Any]:
    """Public wrapper para obtener coordenadas (lat, lon) a partir de una dirección libre."""

    result = await _geocode_address(address_text)
    if result.get("status") != "success":
        return result

    lat = result["lat"]
    lon = result["lon"]
    result["summary_text"] = (
        f"Ubicación aproximada para '{address_text}': lat {lat}, lon {lon}."
    )
    return result


async def find_nearby_services_by_address(
    address_text: str,
    query: str = "gas station",
    radius_meters: int = 2000,
) -> dict[str, Any]:
    """Busca servicios cercanos alrededor de una dirección en texto libre.

    Esta función es más amigable para el agente, ya que no requiere que el modelo
    conozca coordenadas explícitas. Primero geocodifica la dirección y luego
    delega en ``find_nearby_services``.
    """

    geo = await _geocode_address(address_text)
    if geo.get("status") != "success":
        return _error_response(
            geo.get("error_type", "geocoding"),
            f"No pude localizar la dirección de búsqueda: {address_text}",
        )

    lat = geo["lat"]
    lon = geo["lon"]

    services = await find_nearby_services(
        lat=lat,
        lon=lon,
        query=query,
        radius_meters=radius_meters,
    )

    if services.get("status") != "success":
        return services

    # Añadimos contexto de la dirección original en el resumen
    base_summary = services.get("summary_text") or ""
    services["summary_text"] = (
        f"Cerca de '{address_text}' (lat {lat}, lon {lon}):\n{base_summary}"
        if base_summary
        else f"Cerca de '{address_text}' (lat {lat}, lon {lon}) no se encontraron "
        f"lugares de tipo '{query}' en un radio de {radius_meters} metros."
    )

    services["center_address"] = address_text
    return services

