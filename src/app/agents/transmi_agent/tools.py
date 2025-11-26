
"""Tool implementations for the TransmiBot agent."""

from __future__ import annotations

import logging
from typing import Any

from app.services.simit import capture_simit_screenshot_service


logger = logging.getLogger(__name__)


async def get_current_time(city: str) -> dict[str, str]:
    """Mock tool that returns the current time in a specified city."""

    return {"status": "success", "city": city, "time": "10:30 AM", "climate": "sunny"}


async def capture_simit_screenshot(plate: str) -> dict[str, Any]:
    """Tool wrapper that delegates to the Simit service layer.

    Keeping this thin wrapper makes it easy to reuse the same core logic from
    other parts of the application while presenting a simple tool interface.
    """

    result = await capture_simit_screenshot_service(plate=plate)
    # The service already applies the required error-handling strategy.
    return result
