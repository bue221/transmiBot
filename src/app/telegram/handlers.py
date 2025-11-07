from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.agents.transmi_agent.agent import invoke_agent

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 ¡Hola! Soy *TransmiBot*, tu asistente de movilidad en Colombia.\n\n"
        "🚌 Puedo ayudarte a planear rutas de TransMilenio, resolver dudas de transporte y"
        " consultar el estado de multas en Simit.\n"
        "🔧 Cuando haga falta, usaré herramientas integradas para obtener la hora actual o"
        " capturar comprobantes del portal Simit.\n\n"
        "¿Qué quieres hacer hoy?",
        parse_mode="Markdown",
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *Comandos disponibles*\n"
        "• /start – Mensaje de bienvenida y resumen del bot.\n"
        "• /help – Muestra esta lista de comandos.\n\n"
        "También puedes escribirme directamente para: planear rutas de TransMilenio,"
        " conocer horarios o consultar el estado de tu vehículo en Simit.",
        parse_mode="Markdown",
    )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception in Telegram handler", exc_info=context.error)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        logger.warning("Received text handler update without message: %s", update)
        return

    try:
        response = await invoke_agent(update.message.text)
    except Exception:
        logger.exception("Agent invocation failed")
        await update.message.reply_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
        return

    await update.message.reply_text(response)