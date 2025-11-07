import logging
from logging.config import dictConfig

from app.config import get_settings


def configure_logging() -> logging.Logger:
    settings = get_settings()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": settings.log_level,
                }
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": settings.log_level,
                }
            },
        }
    )
    return logging.getLogger("app")

