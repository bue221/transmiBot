from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
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

    chat_id = update.effective_chat.id

    status_message = await update.message.reply_text("Procesando ⏳")

    stop_event = asyncio.Event()

    async def animate_status_message() -> None:
        animation_frames = ["⏳", "⌛"]
        frame_index = 0

        while not stop_event.is_set():
            try:
                new_text = f"Procesando {animation_frames[frame_index]}"
                await status_message.edit_text(new_text)
                frame_index = (frame_index + 1) % len(animation_frames)
                await asyncio.sleep(1)
            except BadRequest as exc:
                if "Message is not modified" not in str(exc):
                    logger.warning("Error animando mensaje: %s", exc)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error inesperado en animate_message: %s", exc)
                return

    async def send_typing_action() -> None:
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(4)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error en keep_typing_action: %s", exc)
                return

    animate_task = asyncio.create_task(animate_status_message())
    typing_task = asyncio.create_task(send_typing_action())

    agent_stream = invoke_agent(update.message.text)

    try:
        first_response = await agent_stream.__anext__()
    except StopAsyncIteration:
        stop_event.set()
        animate_task.cancel()
        typing_task.cancel()
        await asyncio.gather(animate_task, typing_task, return_exceptions=True)
        await agent_stream.aclose()
        await status_message.edit_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
        logger.error("Agent stream completed without responses")
        return
    except Exception:
        stop_event.set()
        animate_task.cancel()
        typing_task.cancel()
        await asyncio.gather(animate_task, typing_task, return_exceptions=True)
        logger.exception("Agent invocation failed before first response")
        await status_message.edit_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
        await agent_stream.aclose()
        return

    stop_event.set()
    animate_task.cancel()
    typing_task.cancel()
    await asyncio.gather(animate_task, typing_task, return_exceptions=True)

    await status_message.edit_text(first_response)

    try:
        async for response_text in agent_stream:
            try:
                await context.bot.send_message(chat_id=chat_id, text=response_text)
            except Exception:
                logger.warning(
                    "Failed to send follow-up agent response",
                    exc_info=True,
                )
    except Exception:
        logger.exception("Agent invocation failed while streaming responses")
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Lo siento, ocurrió un error al consultar al agente. "
                "Inténtalo de nuevo más tarde."
            ),
        )
    finally:
        stop_event.set()
        await agent_stream.aclose()