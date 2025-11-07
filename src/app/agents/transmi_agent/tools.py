
"""Tool implementations for the TransmiBot agent."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


logger = logging.getLogger(__name__)

_SIMIT_BASE_URL: str = "https://www.fcm.org.co/simit/#/estado-cuenta?numDocPlacaProp={plate}"
_DEFAULT_TIMEOUT_MS: int = 20000
_SCREENSHOT_ROOT = Path(__file__).resolve().parents[4] / "var" / "screenshots"
_POST_LOAD_WAIT_MS: int = 7000
_CONTAINER_SELECTOR = ".container-fluid"


def get_current_time(city: str) -> dict[str, str]:
    """Mock tool that returns the current time in a specified city."""

    return {"status": "success", "city": city, "time": "10:30 AM"}


async def capture_simit_screenshot(plate: str) -> dict[str, Any]:
    """Return a base64-encoded screenshot of the Simit account status page for ``plate``.

    Args:
        plate: Vehicle plate or document identifier required by the Simit portal.

    Returns:
        A dictionary containing the screenshot metadata and encoded content. On failure, the
        dictionary includes the error details and ``status`` is set to ``"error"``.
    """

    if plate is None:
        return {
            "status": "error",
            "error_type": "validation",
            "message": "Vehicle plate is required to capture the Simit screenshot.",
        }

    normalized_plate = plate.strip().upper()
    if not normalized_plate:
        return {
            "status": "error",
            "error_type": "validation",
            "message": "Vehicle plate cannot be empty.",
        }

    target_url = _SIMIT_BASE_URL.format(plate=normalized_plate)
    screenshot_bytes: bytes | None = None
    container_texts: list[str] | None = None

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await browser.new_context(viewport={"width": 1280, "height": 720})
                try:
                    page = await context.new_page()

                    logger.info(
                        "Loading Simit account status page", extra={"plate": normalized_plate}
                    )

                    response = await page.goto(
                        target_url, wait_until="networkidle", timeout=_DEFAULT_TIMEOUT_MS
                    )
                    if response and response.status >= 400:
                        logger.warning(
                            "Simit responded with HTTP %s",
                            response.status,
                            extra={"plate": normalized_plate},
                        )

                    await page.wait_for_load_state("networkidle", timeout=_DEFAULT_TIMEOUT_MS)
                    await page.wait_for_timeout(_POST_LOAD_WAIT_MS)

                    container_locator = page.locator(_CONTAINER_SELECTOR)
                    try:
                        await container_locator.first.wait_for(
                            state="visible", timeout=_DEFAULT_TIMEOUT_MS
                        )
                    except PlaywrightTimeoutError:
                        logger.warning(
                            "Timed out waiting for container selector to appear",
                            extra={"plate": normalized_plate, "selector": _CONTAINER_SELECTOR},
                        )
                    else:
                        container_texts = await container_locator.all_inner_texts()

                    screenshot_bytes = await page.screenshot(full_page=True, type="png")
                finally:
                    await context.close()
            finally:
                await browser.close()

    except PlaywrightTimeoutError as exc:
        logger.exception(
            "Timed out waiting for Simit page to finish loading", extra={"plate": normalized_plate}
        )
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Timed out while loading the Simit account page.",
            "details": str(exc),
        }

    except PlaywrightError as exc:
        logger.exception(
            "Playwright failed while capturing Simit screenshot", extra={"plate": normalized_plate}
        )
        return {
            "status": "error",
            "error_type": "playwright",
            "message": "The browser automation failed while capturing the Simit screenshot.",
            "details": str(exc),
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error while capturing Simit screenshot", extra={"plate": normalized_plate}
        )
        return {
            "status": "error",
            "error_type": "unexpected",
            "message": "An unexpected error occurred while capturing the Simit screenshot.",
            "details": str(exc),
        }

    if screenshot_bytes is None:
        return {
            "status": "error",
            "error_type": "unexpected",
            "message": "Failed to capture the Simit screenshot for an unknown reason.",
        }

    screenshot_encoded = base64.b64encode(screenshot_bytes).decode("ascii")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"simit_{normalized_plate}_{timestamp}.png"
    output_path = _SCREENSHOT_ROOT / filename

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(screenshot_bytes)
    except OSError as exc:
        logger.exception(
            "Failed to persist Simit screenshot to disk",
            extra={"plate": normalized_plate, "path": str(output_path)},
        )
        return {
            "status": "error",
            "error_type": "io",
            "message": "Failed to persist the Simit screenshot to disk.",
            "details": str(exc),
        }

    logger.info(
        "Captured Simit screenshot successfully",
        extra={"plate": normalized_plate, "path": str(output_path)},
    )

    return {
        "status": "success",
        "plate": normalized_plate,
        "url": target_url,
        "file_path": str(output_path),
        "container_text": container_texts or [],
        "screenshot": {
            "mime_type": "image/png",
            "encoding": "base64",
            "data": screenshot_encoded,
        },
    }
