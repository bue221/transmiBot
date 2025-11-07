from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hola! Soy TransmiBot. Envíame un mensaje y consultaré al agente de Google para ayudarte."
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "TransmiBot conecta Telegram con un agente de Google. Solo escribe tu pregunta."
    )

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception in Telegram handler", exc_info=context.error)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return update.message.reply_text("Hello, world!")