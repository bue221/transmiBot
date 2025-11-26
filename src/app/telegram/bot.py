from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.telegram.handlers import (
    handle_contact,
    handle_error,
    handle_help,
    handle_start,
    handle_text,
)

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Configure the Telegram application with handlers and middleware."""

    settings = get_settings()
    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .build()
    )

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_help))
    # Handler for when user shares contact (must be before TEXT handler)
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(handle_error)

    return application




