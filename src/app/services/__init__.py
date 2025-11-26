"""Service layer for application features (e.g., persistence, APIs, automation)."""

from .simit import capture_simit_screenshot_service

__all__: list[str] = ["capture_simit_screenshot_service"]


