from __future__ import annotations

import logging
import asyncio

from telegram.error import BadRequest
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

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
    
    message = await update.message.reply_text("Procesando ⏳")
    
    main_task = asyncio.create_task(invoke_agent(update.message.text))
    
    async def animate_message():
        animation_frames = ["⏳", "⌛", "⏳", "⌛"]
        frame_index = 0
        while not main_task.done():
            try:
                new_text = f"Procesando {animation_frames[frame_index]}"
                await message.edit_text(new_text)
                frame_index = (frame_index + 1) % len(animation_frames)
                
                await asyncio.sleep(1) 
                
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    logger.warning(f"Error animando mensaje: {e}")
                    break
            except Exception as e:
                logger.warning(f"Error inesperado en animate_message: {e}")
                break

    async def keep_typing_action():
        while not main_task.done():
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id, 
                    action=ChatAction.TYPING
                )
                await asyncio.sleep(4)
            except Exception as e:
                logger.warning(f"Error en keep_typing_action: {e}")
                break

    anim_task = asyncio.create_task(animate_message())
    typing_task = asyncio.create_task(keep_typing_action())

    try:
        response = await main_task
        
        anim_task.cancel()
        typing_task.cancel()

        await message.edit_text(response)
        
    except Exception:
        logger.exception("Agent invocation failed")
        
        anim_task.cancel()
        typing_task.cancel()
        await message.edit_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
    finally:
        await asyncio.gather(anim_task, typing_task, return_exceptions=True)