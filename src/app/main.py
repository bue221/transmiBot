import logging
from typing import Optional

from app.config import get_settings
from app.exceptions import ConfigurationError, ExternalServiceError
from app.health import HealthServer, start_health_server
from app.logging_config import configure_logging
from app.telegram.bot import build_application


def main() -> None:
    configure_logging()
    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info("Bootstrapping TransmiBot", extra={"env": settings.environment})

    application = build_application()
    health_server: Optional[HealthServer] = None

    try:
        if settings.telegram_webhook_url:
            webhook_url = str(settings.telegram_webhook_url)
            application.run_webhook(
                listen="0.0.0.0",
                port=settings.port,
                url_path=settings.telegram_webhook_path,
                webhook_url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=list(settings.telegram_allowed_updates),
            )
        else:
            try:
                health_server = start_health_server("0.0.0.0", settings.port)
            except OSError as exc:
                logger.exception("Failed to start health server")
                raise ConfigurationError(
                    f"Unable to bind health endpoint to port {settings.port}"
                ) from exc

            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=list(settings.telegram_allowed_updates),
            )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except ExternalServiceError as exc:
        logger.error("Service error: %s", exc)
        raise
    except Exception as exc:  # pragma: no cover - unexpected error boundary
        logger.exception("Unexpected error during runtime")
        raise ConfigurationError("Application crashed") from exc
    finally:
        if health_server is not None:
            health_server.stop()


if __name__ == "__main__":
    main()

